from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.rendering.page_reader import (
    coordinate_authority,
    public_coordinate_authority,
    transform_pixel_polygon_to_unrotated_mpt,
)
from bctc_ai.source_structure.contracts_v1 import (
    AtomAuthority,
    SourceStructureContractError,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    make_empty_page_proposal_set_v1,
    make_source_object_id_v1,
    same_typed_json_v1,
    validate_neutral_page_envelope_v1,
)
from bctc_ai.source_structure.evidence_projection_v1 import (
    LINE_SUPPLEMENT_CLAIM_BOUNDARY,
    LINE_SUPPLEMENT_FORMAT_VERSION,
    SourceEvidenceProjectionError,
    project_authenticated_page_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "a" * 64
BACKEND_SHA = "b" * 64
RENDER_SHA = "c" * 64
OCR_PROVIDER_SHA = "e" * 64
OCR_RENDER_RUNTIME_SHA = "f" * 64
NATIVE_PROVIDER_SHA = "2" * 64

UPSTREAM_SAFETY = {
    "statement_classified": False,
    "table_classified": False,
    "rows_reconstructed": False,
    "cells_interpreted": False,
    "absence_claimed": False,
    "bank_registry_metadata_used": False,
    "filename_metadata_used": False,
    "role_a_used": False,
    "schema_used": False,
    "mapping_used": False,
    "historical_values_used": False,
}
SUPPLEMENT_SAFETY = {
    "page_read_complete_claimed": False,
    "ocr_complete_claimed": False,
    "word_geometry_accepted": False,
    "word_tokens_exposed": False,
    "blank_claimed": False,
    "absence_claimed": False,
    "statement_classification_attempted": False,
    "table_classification_attempted": False,
    "row_reconstruction_attempted": False,
    "cell_interpretation_attempted": False,
    "axis_interpretation_attempted": False,
    "schema_used": False,
    "mapping_used": False,
    "role_a_used": False,
    "historical_values_used": False,
    "bank_registry_metadata_used": False,
    "filename_metadata_used": False,
    "source_path_metadata_used": False,
    "new_ocr_inference_used": False,
    "network_used": False,
    "native_ocr_fallback_used": False,
}


class _Box:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


def _object_ref(digest: str, size: int, suffix: str) -> dict:
    return {
        "path": f"objects/sha256/{digest[:2]}/{digest}{suffix}",
        "sha256": digest,
        "size_bytes": size,
    }


def _json_ref(payload: dict) -> dict:
    encoded = canonical_json_bytes_v1(payload)
    digest = canonical_json_sha256_v1(payload)
    return _object_ref(digest, len(encoded), ".json")


def _request(*, route: str, source_sha: str, page: int) -> tuple[dict, str]:
    ocr = route == "DOMINANT_RASTER_OCR"
    request = {
        "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
        "git_commit": "0" * 40,
        "implementation_ledger_sha256": "1" * 64,
        "input_ledger_sha256": "2" * 64,
        "selection_receipt_sha256": "3" * 64,
        "sentinel_sha256": "4" * 64,
        "route_plan_sha256": "5" * 64,
        "pre_ocr_feature_fingerprint_sha256": "6" * 64,
        "source_sha256": source_sha,
        "source_size_bytes": 4096,
        "physical_page": page,
        "route": route,
        "provider_identity_sha256": OCR_PROVIDER_SHA if ocr else NATIVE_PROVIDER_SHA,
        "render_runtime_identity_sha256": OCR_RENDER_RUNTIME_SHA if ocr else None,
        "render_specification": (
            {
                "dpi": 300,
                "colorspace": "RGB",
                "alpha": False,
                "annotations": "INCLUDED",
                "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
            }
            if ocr
            else None
        ),
        "bank_identity_used": False,
        "filename_used": False,
        "role_a_used": False,
        "schema_used": False,
        "historical_values_used": False,
    }
    return request, canonical_json_sha256_v1(request)


def _ocr_authority(rotation: int) -> tuple[dict, dict]:
    unrotated_width = 600.0
    unrotated_height = 800.0
    if rotation in {0, 180}:
        displayed_width, displayed_height = unrotated_width, unrotated_height
        pixel_width, pixel_height = 1200, 1600
    else:
        displayed_width, displayed_height = unrotated_height, unrotated_width
        pixel_width, pixel_height = 1600, 1200
    page = SimpleNamespace(
        rotation=rotation,
        rect=_Box(displayed_width, displayed_height),
        cropbox=_Box(unrotated_width, unrotated_height),
    )
    private = coordinate_authority(
        page,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )
    return private, public_coordinate_authority(private)


def _ocr_line(private_authority: dict) -> tuple[dict, dict]:
    raw_polygon = [[100, 120], [700, 120], [700, 200], [100, 200]]
    raw_bbox = [100, 120, 700, 200]
    canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(raw_polygon, private_authority)
    canonical_bbox = [
        min(point[0] for point in canonical_polygon),
        min(point[1] for point in canonical_polygon),
        max(point[0] for point in canonical_polygon),
        max(point[1] for point in canonical_polygon),
    ]
    word_polygon = transform_pixel_polygon_to_unrotated_mpt(
        [[100, 120], [300, 120], [300, 200], [100, 200]],
        private_authority,
    )
    word = {
        "raw_text": "0",
        "score": None,
        "score_kind": "PP_OCRV6_LINE_SCORE_ONLY",
        "normalized_pixel_bbox": [100, 120, 300, 200],
        "canonical_bbox_mpt": [
            min(point[0] for point in word_polygon),
            min(point[1] for point in word_polygon),
            max(point[0] for point in word_polygon),
            max(point[1] for point in word_polygon),
        ],
        "canonical_polygon_mpt": word_polygon,
    }
    line = {
        "raw_text": "0",
        "score": 0.95,
        "score_kind": "PP_OCRV6_LINE_RECOGNITION_SCORE",
        "raw_pixel_bbox": raw_bbox,
        "raw_pixel_polygon": raw_polygon,
        "canonical_bbox_mpt": canonical_bbox,
        "canonical_polygon_mpt": canonical_polygon,
        "words": [word],
    }
    return line, word


def _page_record(
    *,
    request: dict,
    request_sha: str,
    result: dict,
    route: str,
    status: str,
    page: int,
    document_id: str | None = None,
) -> dict:
    result_ref = _json_ref(result)
    native = route == "CAUSAL_NATIVE_TEXT"
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1",
        "request_ordinal": page,
        "document_id": document_id or f"sha256:{request['source_sha256']}",
        "source_sha256": request["source_sha256"],
        "source_size_bytes": request["source_size_bytes"],
        "physical_page": page,
        "route": route,
        "request_sha256": request_sha,
        "request": request,
        "status": status,
        "origin": ("SEALED_CAUSAL_NATIVE_TEXT_GATE" if native else "PINNED_PPOCRV6_FULL_READER"),
        "render_ref": None if native else _object_ref(RENDER_SHA, 17, ".png"),
        "backend_payload_ref": _object_ref(BACKEND_SHA, 31, ".json"),
        "result_ref": result_ref,
        "line_count": len(result["lines"]),
        "word_token_count": len(result["words"]),
        "unresolved": status.startswith("UNRESOLVED_"),
        "quarantined_span_count": len(result.get("quarantined_spans", [])),
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }


def _ocr_complete(rotation: int = 0, *, source_sha: str = SOURCE_SHA, page: int = 1):
    private, public = _ocr_authority(rotation)
    request, request_sha = _request(route="DOMINANT_RASTER_OCR", source_sha=source_sha, page=page)
    line, word = _ocr_line(private)
    render_ref = _object_ref(RENDER_SHA, 17, ".png")
    backend_ref = _object_ref(BACKEND_SHA, 31, ".json")
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
        "status": "OCR_WORD_BOX_READ_COMPLETE",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "request_sha256": request_sha,
        "request": request,
        "source_sha256": source_sha,
        "source_size_bytes": 4096,
        "physical_page": page,
        "route": "DOMINANT_RASTER_OCR",
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_runtime_identity_sha256": request["render_runtime_identity_sha256"],
        "input_render_ref": render_ref,
        "backend_payload_ref": backend_ref,
        "word_box_normalization_ledger": {
            "format_version": (
                "BANK_CORPUS_WAVE_1_ROLE_B_PPOCRV6_WORD_BOX_NORMALIZATION_LEDGER_V1"
            ),
            "status": "NO_CHANGE",
            "rule_id": "PP_OCRV6_TEXT_WORD_BOX_PAGE_BOUNDARY_CLIP_MAX_1PX_V1",
            "maximum_per_edge_overshoot_pixels": 1,
            "policy_sha256": "3" * 64,
            "control_identity_sha256": "4" * 64,
            "normalization_producer_implementation_ledger_sha256": "5" * 64,
            "pixel_dimensions": public["pixel_dimensions"],
            "raw_payload_sha256": "6" * 64,
            "normalized_payload_sha256": "6" * 64,
            "correction_count": 0,
            "corrected_edge_count": 0,
            "corrections": [],
        },
        "coordinate_authority": public,
        "lines": [line],
        "words": [word],
        "metrics": {
            "line_count": 1,
            "word_token_count": 1,
            "minimum_line_score": 0.95,
            "mean_line_score": 0.95,
            "lines_below_0_8": 0,
            "lines_below_0_9": 0,
        },
        "source_blank_claimed": False,
        "safety": UPSTREAM_SAFETY,
    }
    return _page_record(
        request=request,
        request_sha=request_sha,
        result=result,
        route="DOMINANT_RASTER_OCR",
        status=result["status"],
        page=page,
    ), result


def _native_complete(*, bbox: list[int] | None = None, page: int = 1):
    request, request_sha = _request(route="CAUSAL_NATIVE_TEXT", source_sha=SOURCE_SHA, page=page)
    word_bbox = bbox or [50_000, 60_000, 150_000, 80_000]
    word = {
        "raw_text": "0",
        "score": None,
        "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
        "canonical_bbox_mpt": word_bbox,
        "block_number": 0,
        "line_number": 0,
        "word_number": 0,
    }
    line = {
        "raw_text": "0",
        "score": None,
        "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
        "canonical_bbox_mpt": word_bbox,
        "block_number": 0,
        "line_number": 0,
        "words": [word],
    }
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1",
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "claim_boundary": "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "document_id": f"sha256:{SOURCE_SHA}",
        "source_sha256": SOURCE_SHA,
        "source_size_bytes": 4096,
        "physical_page": page,
        "route": "CAUSAL_NATIVE_TEXT",
        "request_sha256": request_sha,
        "request": request,
        "full_control_identity_sha256": "1" * 64,
        "provider_identity_sha256": request["provider_identity_sha256"],
        "backend_payload_sha256": BACKEND_SHA,
        "coordinate_authority": {
            "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
            "coordinate_unit": "MILLI_POINT",
            "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
            "pdf_rotation_applied_to_coordinates": False,
        },
        "failure_type": None,
        "native_text_quality": "USABLE_TEXT_LAYER",
        "corruption_markers": [],
        "lines": [line],
        "words": [word],
        "quarantined_spans": [],
        "metrics": {"line_count": 1, "word_token_count": 1, "quarantined_span_count": 0},
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": UPSTREAM_SAFETY,
    }
    return _page_record(
        request=request,
        request_sha=request_sha,
        result=result,
        route="CAUSAL_NATIVE_TEXT",
        status=result["status"],
        page=page,
    ), result


def _native_nonmonotonic_visual_order_complete():
    record, result = _native_complete()
    first_words = [
        {
            "raw_text": "Tài",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [10_000, 20_000, 40_000, 30_000],
            "block_number": 16,
            "line_number": 0,
            "word_number": 0,
        },
        {
            "raw_text": "sản",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [45_000, 20_000, 75_000, 30_000],
            "block_number": 16,
            "line_number": 0,
            "word_number": 1,
        },
    ]
    second_words = [
        {
            "raw_text": "Nợ",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [10_000, 40_000, 30_000, 50_000],
            "block_number": 2,
            "line_number": 0,
            "word_number": 0,
        }
    ]
    result["lines"] = [
        {
            "raw_text": "Tài sản",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [10_000, 20_000, 75_000, 30_000],
            "block_number": 16,
            "line_number": 0,
            "words": first_words,
        },
        {
            "raw_text": "Nợ",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [10_000, 40_000, 30_000, 50_000],
            "block_number": 2,
            "line_number": 0,
            "words": second_words,
        },
    ]
    result["words"] = [*first_words, *second_words]
    result["metrics"] = {
        "line_count": 2,
        "word_token_count": 3,
        "quarantined_span_count": 0,
    }
    record["line_count"] = 2
    record["word_token_count"] = 3
    _refresh_result_ref(record, result)
    return record, result


def _refresh_result_ref(record: dict, result: dict) -> None:
    record["result_ref"] = _json_ref(result)


def _refresh_request_bindings(record: dict, result: dict) -> None:
    result["request"] = deepcopy(record["request"])
    request_sha = canonical_json_sha256_v1(record["request"])
    record["request_sha256"] = request_sha
    result["request_sha256"] = request_sha
    _refresh_result_ref(record, result)


def _refresh_ocr_axis_accounting(record: dict, result: dict) -> None:
    result["words"] = [word for line in result["lines"] for word in line["words"]]
    scores = [line["score"] for line in result["lines"]]
    result["metrics"] = {
        "line_count": len(result["lines"]),
        "word_token_count": len(result["words"]),
        "minimum_line_score": min(scores) if scores else None,
        "mean_line_score": sum(scores) / len(scores) if scores else None,
        "lines_below_0_8": sum(score < 0.8 for score in scores),
        "lines_below_0_9": sum(score < 0.9 for score in scores),
    }
    record["line_count"] = len(result["lines"])
    record["word_token_count"] = len(result["words"])
    _refresh_result_ref(record, result)


def _refresh_neutral_self_references(envelope: dict) -> None:
    """Refresh only neutral self-references, never authenticated upstream-axis digests."""

    receipt = envelope["projection_receipt"]
    receipt["coordinate_authority_sha256"] = canonical_json_sha256_v1(
        envelope["coordinate_authority"]
    )
    locator = envelope["source_locator"]
    page_identity_payload = {
        **locator,
        "route": envelope["route"],
        "upstream_status": envelope["upstream_status"],
        "terminal_reason": envelope["terminal_reason"],
        "evidence_refs": envelope["evidence_refs"],
        "coordinate_authority_sha256": receipt["coordinate_authority_sha256"],
        "projection_source_receipt": {
            key: receipt[key]
            for key in sorted(set(receipt) - {"atom_sequence_sha256", "atom_id_sequence_sha256"})
        },
    }
    page_id = f"ssv1:page:{canonical_json_sha256_v1(page_identity_payload)}"
    envelope["source_local_page_id"] = page_id
    for atom in envelope["atoms"]:
        if atom["quarantine_summary"] is not None:
            atom["quarantine_payload_sha256"] = canonical_json_sha256_v1(
                {
                    key: atom[key]
                    for key in sorted(set(atom) - {"source_local_id", "quarantine_payload_sha256"})
                }
            )
        atom["source_local_id"] = make_source_object_id_v1(
            "atom",
            {
                "source_local_page_id": page_id,
                "request_sha256": locator["request_sha256"],
                "atom_payload": {key: atom[key] for key in sorted(set(atom) - {"source_local_id"})},
            },
        )
    receipt["atom_sequence_sha256"] = canonical_json_sha256_v1(envelope["atoms"])
    receipt["atom_id_sequence_sha256"] = canonical_json_sha256_v1(
        [atom["source_local_id"] for atom in envelope["atoms"]]
    )


def _native_terminal(status: str):
    record, result = _native_complete()
    result["status"] = status
    result["lines"] = []
    result["words"] = []
    result["metrics"] = {
        "line_count": 0,
        "word_token_count": 0,
        "quarantined_span_count": 0,
    }
    if status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        result["failure_type"] = "CausalNativeTextError"
        result["native_text_quality"] = None
        result["corruption_markers"] = []
    elif status == "UNRESOLVED_NATIVE_TEXT_QUALITY":
        result["failure_type"] = None
        result["native_text_quality"] = "NO_TEXT_LAYER"
        result["corruption_markers"] = []
    else:  # pragma: no cover - synthetic fixture guard
        raise AssertionError(status)
    record["status"] = status
    record["line_count"] = 0
    record["word_token_count"] = 0
    record["unresolved"] = True
    _refresh_result_ref(record, result)
    return record, result


def _ocr_terminal(rotation: int = 0):
    _, public = _ocr_authority(rotation)
    request, request_sha = _request(route="DOMINANT_RASTER_OCR", source_sha=SOURCE_SHA, page=3)
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY",
        "request_sha256": request_sha,
        "request": request,
        "source_sha256": SOURCE_SHA,
        "source_size_bytes": 4096,
        "physical_page": 3,
        "route": "DOMINANT_RASTER_OCR",
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_runtime_identity_sha256": request["render_runtime_identity_sha256"],
        "input_render_ref": _object_ref(RENDER_SHA, 17, ".png"),
        "backend_payload_ref": _object_ref(BACKEND_SHA, 31, ".json"),
        "normalization_failure": {
            "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
            "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
            "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
            "policy_sha256": "3" * 64,
            "control_identity_sha256": "4" * 64,
            "normalization_producer_implementation_ledger_sha256": "5" * 64,
            "pixel_dimensions": public["pixel_dimensions"],
            "raw_payload_sha256": "6" * 64,
        },
        "coordinate_authority": public,
        "lines": [],
        "words": [],
        "metrics": {"line_count": 0, "word_token_count": 0},
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": UPSTREAM_SAFETY,
    }
    return _page_record(
        request=request,
        request_sha=request_sha,
        result=result,
        route="DOMINANT_RASTER_OCR",
        status=result["status"],
        page=3,
    ), result


def _line_supplement(record: dict, result: dict) -> tuple[dict, dict]:
    private, _ = _ocr_authority(result["coordinate_authority"]["pdf_rotation_degrees"])
    line, _ = _ocr_line(private)
    observation = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_LINE_OBSERVATION_V1",
        "line_index": 0,
        "text": line["raw_text"],
        "score": line["score"],
        "pixel_rec_box": line["raw_pixel_bbox"],
        "pixel_rec_polygon": line["raw_pixel_polygon"],
        "canonical_rec_box_mpt": line["canonical_bbox_mpt"],
        "canonical_rec_polygon_mpt": line["canonical_polygon_mpt"],
    }
    quarantine = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_WORD_SUBDIVISION_QUARANTINE_V1",
        "status": "QUARANTINED_UNRESOLVED_WORD_BOX_GEOMETRY",
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "ordered_subdivision_counts_by_line": [1],
        "total_subdivision_count": 1,
        "word_axes_sha256": "7" * 64,
        "raw_provider_payload_sha256": result["normalization_failure"]["raw_payload_sha256"],
        "raw_backend_payload_ref": record["backend_payload_ref"],
        "word_text_exposed": False,
        "word_geometry_exposed": False,
        "accepted_word_count": 0,
    }
    supplement = {
        "format_version": LINE_SUPPLEMENT_FORMAT_VERSION,
        "supplemental_disposition": (
            "LINE_ONLY_EVIDENCE_AVAILABLE_FROM_TERMINAL_WORD_BOX_GEOMETRY"
        ),
        "claim_boundary": LINE_SUPPLEMENT_CLAIM_BOUNDARY,
        "control_identity_sha256": "8" * 64,
        "upstream": {
            "aggregate_identity_sha256": "1" * 64,
            "status": record["status"],
            "status_preserved": True,
            "normalization_failure_reason": ("BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"),
            "request_sha256": record["request_sha256"],
            "request_ordinal": record["request_ordinal"],
            "document_id": record["document_id"],
            "physical_page": record["physical_page"],
            "source_sha256": record["source_sha256"],
            "backend_payload_ref": record["backend_payload_ref"],
            "result_ref": record["result_ref"],
            "normalization_failure": result["normalization_failure"],
        },
        "coordinate_authority": result["coordinate_authority"],
        "lines": [observation],
        "words": [],
        "quarantine": quarantine,
        "metrics": {
            "validated_line_axis_count": 1,
            "excluded_empty_line_axis_count": 0,
            "accepted_line_count": 1,
            "accepted_word_count": 0,
            "quarantined_subdivision_count": 1,
        },
        "safety": SUPPLEMENT_SAFETY,
    }
    return supplement, _json_ref(supplement)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_ocr_projection_matches_existing_exact_rotation_authority(rotation: int) -> None:
    record, result = _ocr_complete(rotation)
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    assert projected["coordinate_authority"] == result["coordinate_authority"]
    assert projected["upstream_status"] == "OCR_WORD_BOX_READ_COMPLETE"
    assert projected["metrics"] == {
        "atom_count": 2,
        "upstream_line_axis_count": 1,
        "upstream_word_axis_count": 1,
        "upstream_quarantined_span_axis_count": 0,
        "primary_line_count": 1,
        "primary_word_count": 1,
        "excluded_empty_line_axis_count": 0,
        "excluded_empty_word_axis_count": 0,
        "supplemental_line_count": 0,
        "supplement_validated_line_axis_count": 0,
        "supplement_excluded_empty_line_axis_count": 0,
        "supplement_quarantined_subdivision_count": 0,
        "quarantined_atom_count": 0,
    }
    assert {atom["kind"] for atom in projected["atoms"]} == {"LINE", "WORD"}


def test_ocr_and_native_project_to_same_neutral_text_geometry_kinds() -> None:
    ocr_record, ocr_result = _ocr_complete()
    ocr = project_authenticated_page_v1(page_record=ocr_record, page_result=ocr_result)
    word_bbox = next(atom for atom in ocr["atoms"] if atom["kind"] == "WORD")["canonical_bbox_mpt"]
    native_record, native_result = _native_complete(bbox=word_bbox)
    native = project_authenticated_page_v1(
        page_record=native_record,
        page_result=native_result,
    )
    ocr_word = next(atom for atom in ocr["atoms"] if atom["kind"] == "WORD")
    native_word = next(atom for atom in native["atoms"] if atom["kind"] == "WORD")
    assert (ocr_word["raw_text"], ocr_word["canonical_bbox_mpt"]) == (
        native_word["raw_text"],
        native_word["canonical_bbox_mpt"],
    )
    assert ocr_word["source_local_id"] != native_word["source_local_id"]


def test_native_visual_order_accepts_nonmonotonic_block_ids_and_closes_line_runs() -> None:
    record, result = _native_nonmonotonic_visual_order_complete()
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    assert [
        (atom["upstream_locator"]["block_number"], atom["upstream_locator"]["line_number"])
        for atom in projected["atoms"]
        if atom["kind"] == "LINE"
    ] == [(16, 0), (2, 0)]
    assert [atom["raw_text"] for atom in projected["atoms"] if atom["kind"] == "WORD"] == [
        "Tài",
        "sản",
        "Nợ",
    ]

    repeated_run = deepcopy(projected)
    for atom in repeated_run["atoms"][3:]:
        atom["upstream_locator"]["block_number"] = 16
        atom["upstream_locator"]["line_number"] = 0
    _refresh_neutral_self_references(repeated_run)
    with pytest.raises(SourceStructureContractError, match="repeated or noncontiguous"):
        validate_neutral_page_envelope_v1(repeated_run)

    dropped_run = deepcopy(projected)
    del dropped_run["atoms"][3:]
    dropped_run["metrics"].update(
        {
            "atom_count": 3,
            "upstream_line_axis_count": 1,
            "upstream_word_axis_count": 2,
            "primary_line_count": 1,
            "primary_word_count": 2,
        }
    )
    dropped_run["projection_receipt"]["upstream_line_axis_count"] = 1
    dropped_run["projection_receipt"]["upstream_word_axis_count"] = 2
    _refresh_neutral_self_references(dropped_run)
    with pytest.raises(SourceStructureContractError, match="upstream projection receipt"):
        validate_neutral_page_envelope_v1(dropped_run)

    reordered_runs = deepcopy(projected)
    reordered_runs["atoms"] = reordered_runs["atoms"][3:] + reordered_runs["atoms"][:3]
    _refresh_neutral_self_references(reordered_runs)
    with pytest.raises(SourceStructureContractError, match="upstream projection receipt"):
        validate_neutral_page_envelope_v1(reordered_runs)

    reordered_words = deepcopy(projected)
    reordered_words["atoms"][1], reordered_words["atoms"][2] = (
        reordered_words["atoms"][2],
        reordered_words["atoms"][1],
    )
    _refresh_neutral_self_references(reordered_words)
    with pytest.raises(SourceStructureContractError, match="word axis"):
        validate_neutral_page_envelope_v1(reordered_words)

    negative_record, negative_result = _native_complete()
    negative_bbox = [-1, 60_000, 150_000, 80_000]
    negative_result["lines"][0]["canonical_bbox_mpt"] = negative_bbox
    negative_result["lines"][0]["words"][0]["canonical_bbox_mpt"] = negative_bbox
    negative_result["words"][0]["canonical_bbox_mpt"] = negative_bbox
    _refresh_result_ref(negative_record, negative_result)
    with pytest.raises(SourceEvidenceProjectionError, match="nonnegative canonical"):
        project_authenticated_page_v1(
            page_record=negative_record,
            page_result=negative_result,
        )


def test_terminal_supplement_stays_terminal_and_has_explicit_dispositions() -> None:
    record, result = _ocr_terminal(90)
    supplement, supplement_ref = _line_supplement(record, result)
    projected = project_authenticated_page_v1(
        page_record=record,
        page_result=result,
        line_only_supplement=supplement,
        line_only_supplement_ref=supplement_ref,
    )
    assert projected["terminal"] is True
    assert projected["upstream_status"] == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
    assert projected["terminal_reason"] == ("BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED")
    assert projected["metrics"]["supplemental_line_count"] == 1
    assert projected["metrics"]["quarantined_atom_count"] == 1
    assert {atom["kind"] for atom in projected["atoms"]} == {
        "LINE",
        "QUARANTINED_SUMMARY",
    }
    line = next(atom for atom in projected["atoms"] if atom["kind"] == "LINE")
    assert line["authority"] == AtomAuthority.SUPPLEMENTAL_COARSE_LINE
    assert all(atom["kind"] != "WORD" for atom in projected["atoms"])
    proposal_set = make_empty_page_proposal_set_v1(projected)
    assert proposal_set["proposals"] == []
    assert {disposition["primary_disposition"] for disposition in proposal_set["dispositions"]} == {
        "UPSTREAM_TERMINAL_UNRESOLVED",
        "UPSTREAM_QUARANTINED",
    }


def test_rejected_supplement_retains_only_nonleaking_quarantine_summary() -> None:
    record, result = _ocr_terminal()
    supplement, _ = _line_supplement(record, result)
    supplement["supplemental_disposition"] = (
        "NO_LINE_ONLY_EVIDENCE_AVAILABLE_NO_NONEMPTY_VALID_LINE_TEXT"
    )
    supplement["lines"] = []
    supplement["metrics"]["accepted_line_count"] = 0
    supplement["metrics"]["excluded_empty_line_axis_count"] = 1
    projected = project_authenticated_page_v1(
        page_record=record,
        page_result=result,
        line_only_supplement=supplement,
        line_only_supplement_ref=_json_ref(supplement),
    )
    assert projected["metrics"]["supplemental_line_count"] == 0
    assert projected["metrics"]["quarantined_atom_count"] == 1
    assert [atom["kind"] for atom in projected["atoms"]] == ["QUARANTINED_SUMMARY"]
    summary = projected["atoms"][0]
    assert summary["raw_text"] is None
    assert summary["canonical_bbox_mpt"] is None
    assert summary["pixel_bbox"] is None
    assert "word" not in summary["quarantine_summary"]


def test_supplement_cannot_expose_words_or_nonfinite_scores() -> None:
    record, result = _ocr_terminal()
    supplement, supplement_ref = _line_supplement(record, result)
    exposed = deepcopy(supplement)
    exposed["words"] = [{"text": "forbidden"}]
    with pytest.raises(SourceEvidenceProjectionError, match="exposed word"):
        project_authenticated_page_v1(
            page_record=record,
            page_result=result,
            line_only_supplement=exposed,
            line_only_supplement_ref=supplement_ref,
        )

    nonfinite = deepcopy(supplement)
    nonfinite["lines"][0]["score"] = float("nan")
    with pytest.raises(SourceEvidenceProjectionError, match="score semantics"):
        project_authenticated_page_v1(
            page_record=record,
            page_result=result,
            line_only_supplement=nonfinite,
            line_only_supplement_ref=supplement_ref,
        )


def test_typed_and_canonical_reference_tampering_fails_closed() -> None:
    record, result = _ocr_complete()
    typed = deepcopy(record)
    typed["source_size_bytes"] = 4096.0
    with pytest.raises(SourceEvidenceProjectionError, match="source size"):
        project_authenticated_page_v1(page_record=typed, page_result=result)

    changed = deepcopy(result)
    changed["metrics"]["line_count"] = 1.0
    with pytest.raises(SourceEvidenceProjectionError, match="reference identity"):
        project_authenticated_page_v1(page_record=record, page_result=changed)

    bad_ref = deepcopy(record)
    bad_ref["result_ref"]["path"] = "objects/sha256/00/not-content-addressed.json"
    with pytest.raises(SourceEvidenceProjectionError, match="locator drifted"):
        project_authenticated_page_v1(page_record=bad_ref, page_result=result)


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("UNRESOLVED_CAUSAL_NATIVE_VISIBILITY", "CausalNativeTextError"),
        ("UNRESOLVED_NATIVE_TEXT_QUALITY", "NO_TEXT_LAYER"),
    ],
)
def test_native_terminal_reason_variants_are_preserved_and_bound(status: str, reason: str) -> None:
    record, result = _native_terminal(status)
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    assert projected["terminal"] is True
    assert projected["upstream_status"] == status
    assert projected["terminal_reason"] == reason
    assert projected["atoms"] == []
    assert make_empty_page_proposal_set_v1(projected)["dispositions"] == []

    tampered = deepcopy(projected)
    tampered["terminal_reason"] = "DifferentSafeFailure"
    with pytest.raises(SourceStructureContractError, match="terminal reason|identity"):
        validate_neutral_page_envelope_v1(tampered)


def test_bool_and_nonfinite_geometry_or_scores_fail_closed() -> None:
    record, result = _ocr_complete()
    bool_coordinate = deepcopy(result)
    bool_coordinate["lines"][0]["raw_pixel_bbox"][0] = True
    _refresh_result_ref(record, bool_coordinate)
    with pytest.raises(SourceEvidenceProjectionError, match="finite coordinates"):
        project_authenticated_page_v1(page_record=record, page_result=bool_coordinate)

    record, result = _ocr_complete()
    bool_coefficient = deepcopy(result)
    bool_coefficient["coordinate_authority"]["pixel_to_unrotated_mpt"][0][0]["numerator"] = True
    _refresh_result_ref(record, bool_coefficient)
    with pytest.raises(SourceEvidenceProjectionError, match="rational coefficient"):
        project_authenticated_page_v1(page_record=record, page_result=bool_coefficient)

    record, result = _ocr_complete()
    bool_score = deepcopy(result)
    bool_score["lines"][0]["score"] = True
    _refresh_result_ref(record, bool_score)
    with pytest.raises(SourceEvidenceProjectionError, match="score semantics"):
        project_authenticated_page_v1(page_record=record, page_result=bool_score)

    record, result = _ocr_complete()
    nonfinite_score = deepcopy(result)
    nonfinite_score["lines"][0]["score"] = float("inf")
    with pytest.raises(SourceStructureContractError, match="non-finite"):
        project_authenticated_page_v1(page_record=record, page_result=nonfinite_score)

    nonfinite_coordinate = deepcopy(result)
    nonfinite_coordinate["lines"][0]["raw_pixel_bbox"][0] = float("inf")
    with pytest.raises(SourceStructureContractError, match="non-finite"):
        project_authenticated_page_v1(page_record=record, page_result=nonfinite_coordinate)


def test_duplicate_and_extra_neutral_reference_kinds_are_rejected() -> None:
    record, result = _ocr_complete()
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    duplicate = deepcopy(projected)
    duplicate["evidence_refs"].append(deepcopy(duplicate["evidence_refs"][0]))
    with pytest.raises(SourceStructureContractError, match="reference accounting"):
        validate_neutral_page_envelope_v1(duplicate)

    extra = deepcopy(projected)
    extra["evidence_refs"].append(
        {
            "kind": "LINE_SUPPLEMENT",
            "sha256": "0" * 64,
            "size_bytes": 1,
            "media_type": "application/json",
            "upstream_reference_sha256": "1" * 64,
        }
    )
    with pytest.raises(SourceStructureContractError, match="reference set"):
        validate_neutral_page_envelope_v1(extra)


def test_request_and_result_schemas_are_exact_and_cross_bound() -> None:
    record, result = _ocr_complete()
    record["request"]["role_a_answer"] = {
        "report_norm_id": "forbidden",
        "bank": "forbidden",
    }
    _refresh_request_bindings(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="request.*fields"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    record["request"]["format_version"] = "SYNTHETIC_AUTHENTICATED_REQUEST_V1"
    _refresh_request_bindings(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="request format"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["role_a_answer"] = {"report_norm_id": "forbidden", "bank": "forbidden"}
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="result fields"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    record["document_id"] = "sha256:" + "d" * 64
    with pytest.raises(SourceEvidenceProjectionError, match="source-content-bound"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["provider_identity_sha256"] = "9" * 64
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="provider identity"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["render_runtime_identity_sha256"] = "9" * 64
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="render runtime identity"):
        project_authenticated_page_v1(page_record=record, page_result=result)


def test_terminal_and_native_status_marker_invariants_are_closed() -> None:
    record, result = _ocr_terminal()
    result["ocr_fallback_used"] = True
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="OCR fallback"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _native_complete()
    result["ocr_fallback_used"] = True
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="OCR fallback"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _native_complete()
    result["corruption_markers"] = ["UNAUTHENTICATED_MARKER"]
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="quality"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _native_terminal("UNRESOLVED_NATIVE_TEXT_QUALITY")
    result["native_text_quality"] = "CORRUPT_TEXT_LAYER"
    result["corruption_markers"] = []
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="text-quality"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    for unsupported_version in (
        "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2",
        "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V3",
    ):
        record, result = _native_complete()
        result["format_version"] = unsupported_version
        _refresh_result_ref(record, result)
        with pytest.raises(SourceEvidenceProjectionError, match="format is unsupported"):
            project_authenticated_page_v1(page_record=record, page_result=result)


def test_integer_boolean_float_drift_is_rejected_everywhere() -> None:
    record, result = _ocr_complete()
    record["line_count"] = True
    with pytest.raises(SourceEvidenceProjectionError, match="line_count"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["metrics"]["word_token_count"] = 1.0
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="word_token_count"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["metrics"]["lines_below_0_8"] = False
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="lines_below_0_8"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["metrics"]["lines_below_0_9"] = 0.0
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="lines_below_0_9"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    record["request"]["render_specification"]["dpi"] = 300.0
    _refresh_request_bindings(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="render specification"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_terminal()
    supplement, _ = _line_supplement(record, result)
    supplement["lines"][0]["score"] = 0
    with pytest.raises(SourceEvidenceProjectionError, match="score semantics"):
        project_authenticated_page_v1(
            page_record=record,
            page_result=result,
            line_only_supplement=supplement,
            line_only_supplement_ref=_json_ref(supplement),
        )


def test_input_geometry_and_coordinate_mutations_fail_after_reference_refresh() -> None:
    record, result = _ocr_complete()
    result["coordinate_authority"]["pdf_rotation_degrees"] = 270
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="dimensions|transform"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["lines"][0]["raw_pixel_bbox"] = [9999, 120, 0, 200]
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="positive area"):
        project_authenticated_page_v1(page_record=record, page_result=result)

    record, result = _ocr_complete()
    result["lines"][0]["canonical_polygon_mpt"] = None
    _refresh_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionError, match="polygon"):
        project_authenticated_page_v1(page_record=record, page_result=result)


def test_bounded_one_pixel_word_box_correction_schema_projects_exactly() -> None:
    record, result = _ocr_complete()
    private, _ = _ocr_authority(0)
    line_polygon = [[0, 120], [700, 120], [700, 200], [0, 200]]
    line_canonical = transform_pixel_polygon_to_unrotated_mpt(line_polygon, private)
    line = result["lines"][0]
    line["raw_pixel_bbox"] = [0, 120, 700, 200]
    line["raw_pixel_polygon"] = line_polygon
    line["canonical_polygon_mpt"] = line_canonical
    line["canonical_bbox_mpt"] = [
        min(point[0] for point in line_canonical),
        min(point[1] for point in line_canonical),
        max(point[0] for point in line_canonical),
        max(point[1] for point in line_canonical),
    ]
    word = line["words"][0]
    word["normalized_pixel_bbox"] = [0, 120, 300, 200]
    word_canonical = transform_pixel_polygon_to_unrotated_mpt(
        [[0, 120], [300, 120], [300, 200], [0, 200]],
        private,
    )
    word["canonical_polygon_mpt"] = word_canonical
    word["canonical_bbox_mpt"] = [
        min(point[0] for point in word_canonical),
        min(point[1] for point in word_canonical),
        max(point[0] for point in word_canonical),
        max(point[1] for point in word_canonical),
    ]
    ledger = result["word_box_normalization_ledger"]
    ledger.update(
        {
            "status": "PAGE_BOUNDARY_CLIPPED",
            "raw_payload_sha256": "7" * 64,
            "normalized_payload_sha256": "8" * 64,
            "correction_count": 1,
            "corrected_edge_count": 1,
            "corrections": [
                {
                    "json_path": "$.text_word_boxes[0][0]",
                    "line_index": 0,
                    "word_index": 0,
                    "raw_box": [-0.5, 120, 300, 200],
                    "normalized_box": [0, 120, 300, 200],
                    "per_edge_clip_pixels": {
                        "left": 0.5,
                        "top": 0,
                        "right": 0,
                        "bottom": 0,
                    },
                    "validated_line_rec_box": [0, 120, 700, 200],
                }
            ],
        }
    )
    record["word_box_correction_count"] = 1
    record["word_box_corrected_edge_count"] = 1
    _refresh_ocr_axis_accounting(record, result)
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    word_atom = next(atom for atom in projected["atoms"] if atom["kind"] == "WORD")
    assert word_atom["pixel_bbox"] == [0, 120, 300, 200]


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_line_only_rec_box_is_authoritative_and_inner_polygon_is_contained(rotation: int) -> None:
    record, result = _ocr_terminal(rotation)
    supplement, _ = _line_supplement(record, result)
    private, _ = _ocr_authority(rotation)
    inner_polygon = [[120, 130], [680, 130], [680, 190], [120, 190]]
    observation = supplement["lines"][0]
    observation["pixel_rec_polygon"] = inner_polygon
    observation["canonical_rec_polygon_mpt"] = transform_pixel_polygon_to_unrotated_mpt(
        inner_polygon,
        private,
    )
    observation["text"] = " \u00a0\u200b"
    observation["score"] = -0.0
    projected = project_authenticated_page_v1(
        page_record=record,
        page_result=result,
        line_only_supplement=supplement,
        line_only_supplement_ref=_json_ref(supplement),
    )
    line = next(atom for atom in projected["atoms"] if atom["kind"] == "LINE")
    assert line["raw_text"] == " \u00a0\u200b"
    assert same_typed_json_v1(line["score"], -0.0)
    assert not same_typed_json_v1(line["score"], 0.0)

    polygon_bbox = [
        min(point[0] for point in observation["canonical_rec_polygon_mpt"]),
        min(point[1] for point in observation["canonical_rec_polygon_mpt"]),
        max(point[0] for point in observation["canonical_rec_polygon_mpt"]),
        max(point[1] for point in observation["canonical_rec_polygon_mpt"]),
    ]
    observation["canonical_rec_box_mpt"] = polygon_bbox
    with pytest.raises(SourceEvidenceProjectionError, match="rec-box/polygon authority"):
        project_authenticated_page_v1(
            page_record=record,
            page_result=result,
            line_only_supplement=supplement,
            line_only_supplement_ref=_json_ref(supplement),
        )


def test_empty_ocr_axes_are_explicitly_excluded_but_whitespace_is_primary() -> None:
    record, result = _ocr_complete()
    result["lines"][0]["raw_text"] = ""
    result["lines"][0]["words"][0]["raw_text"] = ""
    _refresh_ocr_axis_accounting(record, result)
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    assert [atom["kind"] for atom in projected["atoms"]] == [
        "EXCLUDED_EMPTY_LINE",
        "EXCLUDED_EMPTY_WORD",
    ]
    assert projected["metrics"]["upstream_line_axis_count"] == 1
    assert projected["metrics"]["upstream_word_axis_count"] == 1
    assert projected["metrics"]["excluded_empty_line_axis_count"] == 1
    assert projected["metrics"]["excluded_empty_word_axis_count"] == 1
    assert projected["metrics"]["quarantined_atom_count"] == 2

    record, result = _ocr_complete()
    whitespace = " \u00a0\u200b"
    result["lines"][0]["raw_text"] = whitespace
    result["lines"][0]["words"][0]["raw_text"] = whitespace
    _refresh_ocr_axis_accounting(record, result)
    projected = project_authenticated_page_v1(page_record=record, page_result=result)
    assert [atom["kind"] for atom in projected["atoms"]] == ["LINE", "WORD"]
    assert [atom["raw_text"] for atom in projected["atoms"]] == [whitespace, whitespace]


def test_standalone_neutral_validation_rejects_self_reference_refreshed_tampering() -> None:
    record, result = _ocr_complete()
    original = project_authenticated_page_v1(page_record=record, page_result=result)

    rotation = deepcopy(original)
    rotation["coordinate_authority"]["pdf_rotation_degrees"] = 270
    _refresh_neutral_self_references(rotation)
    with pytest.raises(SourceStructureContractError, match="dimensions|transform"):
        validate_neutral_page_envelope_v1(rotation)

    inverted = deepcopy(original)
    inverted["atoms"][0]["pixel_bbox"] = [9999, 120, 0, 200]
    _refresh_neutral_self_references(inverted)
    with pytest.raises(SourceStructureContractError, match="positive area"):
        validate_neutral_page_envelope_v1(inverted)

    dropped = deepcopy(original)
    dropped["atoms"].pop()
    dropped["metrics"]["atom_count"] = 1
    dropped["metrics"]["upstream_word_axis_count"] = 0
    dropped["metrics"]["primary_word_count"] = 0
    dropped["projection_receipt"]["upstream_word_axis_count"] = 0
    _refresh_neutral_self_references(dropped)
    with pytest.raises(SourceStructureContractError, match="projection|text|no-drop"):
        validate_neutral_page_envelope_v1(dropped)

    reordered = deepcopy(original)
    reordered["atoms"].reverse()
    _refresh_neutral_self_references(reordered)
    with pytest.raises(SourceStructureContractError, match="sequence|axis"):
        validate_neutral_page_envelope_v1(reordered)

    geometry_removed = deepcopy(original)
    del geometry_removed["atoms"][0]["pixel_polygon"]
    _refresh_neutral_self_references(geometry_removed)
    with pytest.raises(SourceStructureContractError, match="fields drifted"):
        validate_neutral_page_envelope_v1(geometry_removed)

    text_removed = deepcopy(original)
    text_removed["atoms"][0]["raw_text"] = None
    text_removed["atoms"][0]["raw_text_sha256"] = None
    _refresh_neutral_self_references(text_removed)
    with pytest.raises(SourceStructureContractError, match="exact nonempty NO_TRIM"):
        validate_neutral_page_envelope_v1(text_removed)

    changed_text = deepcopy(original)
    for atom in changed_text["atoms"]:
        atom["raw_text"] = "7"
        atom["raw_text_sha256"] = sha256(b"7").hexdigest()
    _refresh_neutral_self_references(changed_text)
    with pytest.raises(SourceStructureContractError, match="upstream projection receipt"):
        validate_neutral_page_envelope_v1(changed_text)

    changed_geometry = deepcopy(original)
    private, _ = _ocr_authority(0)
    raw_polygon = [[110, 120], [710, 120], [710, 200], [110, 200]]
    canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(raw_polygon, private)
    line = changed_geometry["atoms"][0]
    line["pixel_bbox"] = [110, 120, 710, 200]
    line["pixel_polygon"] = raw_polygon
    line["canonical_polygon_mpt"] = canonical_polygon
    line["canonical_bbox_mpt"] = [
        min(point[0] for point in canonical_polygon),
        min(point[1] for point in canonical_polygon),
        max(point[0] for point in canonical_polygon),
        max(point[1] for point in canonical_polygon),
    ]
    _refresh_neutral_self_references(changed_geometry)
    with pytest.raises(SourceStructureContractError, match="upstream projection receipt"):
        validate_neutral_page_envelope_v1(changed_geometry)

    terminal_record, terminal_result = _ocr_terminal()
    supplement, supplement_ref = _line_supplement(terminal_record, terminal_result)
    terminal = project_authenticated_page_v1(
        page_record=terminal_record,
        page_result=terminal_result,
        line_only_supplement=supplement,
        line_only_supplement_ref=supplement_ref,
    )
    terminal_line = next(atom for atom in terminal["atoms"] if atom["kind"] == "LINE")
    terminal_line["raw_text"] = "forged supplement text"
    terminal_line["raw_text_sha256"] = sha256(terminal_line["raw_text"].encode()).hexdigest()
    _refresh_neutral_self_references(terminal)
    with pytest.raises(SourceStructureContractError, match="upstream projection receipt"):
        validate_neutral_page_envelope_v1(terminal)


def test_projection_import_closure_excludes_pipeline_answer_sources() -> None:
    allowed_internal = {"bctc_ai.source_structure.contracts_v1"}
    for relative in (
        "src/bctc_ai/source_structure/contracts_v1.py",
        "src/bctc_ai/source_structure/evidence_projection_v1.py",
    ):
        tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        internal = {name for name in imported if name.startswith("bctc_ai.")}
        assert internal <= allowed_internal
        forbidden = ("mapping", "reference", "evaluation", "schema", "history")
        assert not any(part in name.casefold() for name in internal for part in forbidden)
        all_imported = set(imported)
        all_imported.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert {"os", "pathlib", "glob"}.isdisjoint(all_imported)

    assert list(inspect.signature(project_authenticated_page_v1).parameters) == [
        "page_record",
        "page_result",
        "line_only_supplement",
        "line_only_supplement_ref",
    ]


def test_projected_keys_have_no_identity_hint_or_filesystem_locator_fields() -> None:
    record, result = _ocr_complete()
    projected = project_authenticated_page_v1(page_record=record, page_result=result)

    def keys(value):
        if isinstance(value, list):
            return {item for child in value for item in keys(child)}
        if not isinstance(value, dict):
            return set()
        return set(value) | {item for child in value.values() for item in keys(child)}

    folded = {key.casefold() for key in keys(projected)}
    for forbidden in (
        "bank",
        "path",
        "filename",
        "role_a",
        "schema",
        "history",
        "historical",
        "reportnormid",
    ):
        assert not any(forbidden in key for key in folded)
