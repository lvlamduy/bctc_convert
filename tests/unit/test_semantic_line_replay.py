from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage
from bctc_ai.evaluation.semantic_line_replay import (
    SemanticLineReplayError,
    build_frozen_semantic_proposals,
)
from bctc_ai.ocr.semantic_line_fusion import SemanticFieldRole


def _evidence():
    line = OCRLine("BÁO CÁO TINH HINH", (10.0, 20.0, 300.0, 50.0), 0.8)
    pages = (OCRPage(page=1, width=1000, height=1400, lines=(line,)),)
    crop = {
        "sample_id": "doc-p01-title",
        "document": "DOC",
        "page": 1,
        "category": "TITLE",
        "expected_text": "BÁO CÁO TÌNH HÌNH",
        "ppocr_result_index": 0,
        "ppocr_bbox": [10, 20, 300, 50],
        "ppocr_text": line.text,
        "crop_path": "crop.png",
        "crop_sha256": "a" * 64,
    }
    manifest = {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "sample_count": 1,
        "samples": [crop],
    }
    prediction = {
        "sample_id": crop["sample_id"],
        "category": crop["category"],
        "crop_path": crop["crop_path"],
        "crop_sha256": crop["crop_sha256"],
        "status": "PARSED_SEMANTIC_PROPOSAL_ONLY",
        "proposal_text": "BÁO CÁO TÌNH HÌNH",
        "reader_score": None,
    }
    inference = {
        "format_version": 1,
        "experiment_id": "E-0026",
        "state": "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "reference_text_available_to_reader": False,
        "sample_count": 1,
        "samples": [prediction],
        "authority": {"automatic_truth_promotion": False, "numeric_value": False},
    }
    return pages, manifest, inference


def test_builds_source_bound_proposal_without_reading_expected_text():
    pages, manifest, inference = _evidence()
    changed_reference = deepcopy(manifest)
    changed_reference["samples"][0]["expected_text"] = "THIS MUST BE IGNORED"

    first = build_frozen_semantic_proposals(
        crop_manifest=manifest,
        inference_result=inference,
        geometry_pages=pages,
        document="DOC",
        reader="DEEPSEEK_OCR_2",
    )
    second = build_frozen_semantic_proposals(
        crop_manifest=changed_reference,
        inference_result=inference,
        geometry_pages=pages,
        document="DOC",
        reader="DEEPSEEK_OCR_2",
    )

    assert first == second
    assert first.expected_or_reference_fields_read is False
    assert first.ppocr_source_text_and_bbox_verified is True
    assert first.proposals[0].field_role is SemanticFieldRole.TITLE
    assert first.proposals[0].source_bboxes == (pages[0].lines[0].bbox,)


def test_skips_structurally_rejected_reader_output_without_creating_text():
    pages, manifest, inference = _evidence()
    inference["samples"][0]["status"] = "REJECT_OUTPUT_CHARACTER_BUDGET_EXCEEDED"
    inference["samples"][0]["proposal_text"] = ""

    built = build_frozen_semantic_proposals(
        crop_manifest=manifest,
        inference_result=inference,
        geometry_pages=pages,
        document="DOC",
        reader="DEEPSEEK_OCR_2",
    )

    assert built.proposals == ()
    assert built.skipped_sample_ids == ("doc-p01-title",)


def test_rejects_any_inference_authority_or_source_drift():
    pages, manifest, inference = _evidence()
    unsafe = deepcopy(inference)
    unsafe["authority"]["automatic_truth_promotion"] = True

    with pytest.raises(SemanticLineReplayError, match="forbidden authority"):
        build_frozen_semantic_proposals(
            crop_manifest=manifest,
            inference_result=unsafe,
            geometry_pages=pages,
            document="DOC",
            reader="DEEPSEEK_OCR_2",
        )

    drifted = deepcopy(manifest)
    drifted["samples"][0]["ppocr_text"] = "different"
    with pytest.raises(SemanticLineReplayError, match="source text/bbox drifted"):
        build_frozen_semantic_proposals(
            crop_manifest=drifted,
            inference_result=inference,
            geometry_pages=pages,
            document="DOC",
            reader="DEEPSEEK_OCR_2",
        )
