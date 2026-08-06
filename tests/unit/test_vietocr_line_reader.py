from __future__ import annotations

import pytest

from bctc_ai.ocr.vietocr_line_reader import (
    VietOCRLineReaderError,
    validate_reference_blind_request,
)


def _request():
    return {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "git_commit": "deadbeef",
        "git_dirty": False,
        "crop_manifest": {"path": "manifest.json", "sha256": "abc"},
        "reference_text_available_to_reader": False,
        "sample_count": 1,
        "samples": [
            {
                "sample_id": "sample-1",
                "category": "TITLE",
                "crop_path": "crop.png",
                "crop_sha256": "def",
            }
        ],
    }


def test_accepts_exact_reference_blind_allowlist():
    samples = validate_reference_blind_request(_request())

    assert samples == [
        {
            "sample_id": "sample-1",
            "category": "TITLE",
            "crop_path": "crop.png",
            "crop_sha256": "def",
        }
    ]


@pytest.mark.parametrize("field", ["expected_text", "reference", "ppocr_text"])
def test_rejects_any_reference_or_baseline_field(field):
    request = _request()
    request["samples"][0][field] = "forbidden"

    with pytest.raises(VietOCRLineReaderError, match="forbidden"):
        validate_reference_blind_request(request)


def test_rejects_reference_availability_flag():
    request = _request()
    request["reference_text_available_to_reader"] = True

    with pytest.raises(VietOCRLineReaderError, match="identity or role"):
        validate_reference_blind_request(request)
