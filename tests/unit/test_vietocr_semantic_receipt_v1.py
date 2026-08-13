from __future__ import annotations

from copy import deepcopy

import pytest
from test_source_structure_evidence_projection_v2 import _synthetic_ocr_pair

from bctc_ai.core.text import normalize_text
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.vietocr_semantic_receipt_v1 import (
    CLAIM_BOUNDARY,
    FORMAT_VERSION,
    VietOCRSemanticReceiptV1Error,
    bind_vietocr_semantic_page_v1,
    validate_vietocr_semantic_receipt_payload_v1,
)

_RECEIPT_SAFETY = {
    "reader_output_is_proposal_only": True,
    "union_samples_diagnostic_only": True,
    "geometry_authority": False,
    "numeric_authority": False,
    "period_authority": False,
    "unit_authority": False,
    "sign_authority": False,
    "scope_authority": False,
    "schema_authority": False,
    "semantic_acceptance": False,
    "automatic_truth_promotion": False,
}


def _projection_and_receipt() -> tuple[dict, dict]:
    record, result = _synthetic_ocr_pair()
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    line_atom = next(
        atom
        for atom in projection["neutral_page_v1"]["atoms"]
        if atom["kind"] == "LINE" and atom["authority"] == "AUTHENTICATED_PRIMARY"
    )
    raw_prediction = "Nợ   đủ tiêu chuẩn"
    receipt = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "experiment_id": "E-0024",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "inputs": {
            name: {
                "path": f"evidence/{name}.json",
                "sha256": character * 64,
                "size_bytes": 100 + index,
            }
            for index, (name, character) in enumerate(
                (
                    ("crop_manifest", "1"),
                    ("reader_request", "2"),
                    ("ocr_result", "3"),
                    ("run_manifest", "4"),
                )
            )
        },
        "pages": [
            {
                "page_id": "page-0001",
                "result_ref": {
                    "path": record["result_ref"]["path"],
                    "sha256": projection["page_result_sha256"],
                    "size_bytes": record["result_ref"]["size_bytes"],
                },
                "render_ref": deepcopy(result["input_render_ref"]),
                "authenticated_line_count": 1,
                "single_line_sample_count": 1,
                "diagnostic_union_sample_count": 0,
            }
        ],
        "samples": [
            {
                "sample_id": "page-0001-line-000",
                "page_id": "page-0001",
                "grouping": "LINE",
                "category": "SOURCE_BOUND_LABEL_LANE_CANDIDATE",
                "source_line_indices": [0],
                "source_bbox_raw_pixels": deepcopy(line_atom["pixel_bbox"]),
                "padded_source_bbox_raw_pixels": [92, 116, 708, 204],
                "crop_ref": {
                    "path": "crops/page-0001-line-000.png",
                    "sha256": "5" * 64,
                    "size_bytes": 123,
                },
                "raw_prediction": raw_prediction,
                "normalized_prediction": normalize_text(raw_prediction),
                "mean_decoded_character_probability": 0.93,
                "processed_dimensions": [240, 32],
                "diagnostic_only": False,
            }
        ],
        "metrics": {
            "page_count": 1,
            "sample_count": 1,
            "single_line_sample_count": 1,
            "diagnostic_union_sample_count": 0,
        },
        "safety": deepcopy(_RECEIPT_SAFETY),
    }
    return projection, receipt


def test_page_binding_rejects_syntax_only_receipt_without_replay_authority() -> None:
    projection, receipt = _projection_and_receipt()

    with pytest.raises(VietOCRSemanticReceiptV1Error, match="replay-authenticated"):
        bind_vietocr_semantic_page_v1(projection, receipt)

    forged = deepcopy(receipt)
    forged["samples"][0]["raw_prediction"] = "Nợ giả mạo"
    forged["samples"][0]["normalized_prediction"] = "Nợ giả mạo"
    with pytest.raises(VietOCRSemanticReceiptV1Error, match="replay-authenticated"):
        bind_vietocr_semantic_page_v1(projection, forged)


def test_closed_receipt_rejects_authority_normalization_and_diagnostic_drift() -> None:
    _projection, receipt = _projection_and_receipt()
    assert validate_vietocr_semantic_receipt_payload_v1(receipt) == receipt

    unsafe = deepcopy(receipt)
    unsafe["safety"]["semantic_acceptance"] = True
    with pytest.raises(VietOCRSemanticReceiptV1Error, match="safety"):
        validate_vietocr_semantic_receipt_payload_v1(unsafe)

    renormalized = deepcopy(receipt)
    renormalized["samples"][0]["normalized_prediction"] = "different"
    with pytest.raises(VietOCRSemanticReceiptV1Error, match="normalization"):
        validate_vietocr_semantic_receipt_payload_v1(renormalized)

    promoted = deepcopy(receipt)
    promoted["samples"][0]["diagnostic_only"] = True
    with pytest.raises(VietOCRSemanticReceiptV1Error, match="diagnostic"):
        validate_vietocr_semantic_receipt_payload_v1(promoted)


def test_page_binding_rejects_even_validated_but_unauthenticated_payload() -> None:
    projection, receipt = _projection_and_receipt()
    validated = validate_vietocr_semantic_receipt_payload_v1(receipt)

    with pytest.raises(VietOCRSemanticReceiptV1Error, match="replay-authenticated"):
        bind_vietocr_semantic_page_v1(projection, validated)
