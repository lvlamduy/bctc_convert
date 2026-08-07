from __future__ import annotations

import pytest

from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)


def _request() -> dict:
    return {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        "git_commit": "a" * 40,
        "git_dirty": False,
        "crop_manifest": {
            "path": "output/calibration/e0035/crop_manifest.json",
            "sha256": "b" * 64,
        },
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": [
            {
                "sample_id": f"page-0003-row-{index:03d}-label",
                "category": "LOGICAL_ROW_LABEL",
                "crop_path": f"output/calibration/e0035/crops/row-{index:03d}.png",
                "crop_sha256": f"{index:064x}",
            }
            for index in range(64)
        ],
    }


def test_contract_accepts_exact_reference_blind_64_crop_request():
    samples = validate_logical_row_label_reader_request(_request())

    assert len(samples) == 64
    assert set(samples[0]) == {"sample_id", "category", "crop_path", "crop_sha256"}


def test_contract_rejects_primary_text_even_when_other_fields_are_valid():
    request = _request()
    request["samples"][0]["ppocr_text"] = "forbidden"

    with pytest.raises(LogicalRowLabelReaderContractError, match="forbidden field"):
        validate_logical_row_label_reader_request(request)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sample_count", 63),
        ("reference_text_available_to_reader", True),
    ],
)
def test_contract_rejects_denominator_or_reference_isolation_drift(field, value):
    request = _request()
    request[field] = value

    with pytest.raises(LogicalRowLabelReaderContractError, match="identity or reference"):
        validate_logical_row_label_reader_request(request)


def test_contract_rejects_crop_path_escape():
    request = _request()
    request["samples"][0]["crop_path"] = "../reviewed-answer.png"

    with pytest.raises(LogicalRowLabelReaderContractError, match="sample identity"):
        validate_logical_row_label_reader_request(request)
