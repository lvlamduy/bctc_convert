from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.experiments import build_loan_maturity_full_document_vietocr_request_v1 as builder


def _request() -> dict[str, object]:
    return {
        "crop_manifest": {
            "path": "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json",
            "sha256": "1" * 64,
        },
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "experiment_id": "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1",
        "format_version": 2,
        "git_commit": "2" * 40,
        "git_dirty": False,
        "reference_text_available_to_reader": False,
        "sample_count": 2,
        "samples": [
            {
                "category": "FULL_DOCUMENT_AUTHENTICATED_LINE",
                "crop_path": (
                    "output/development/loan-maturity-full-document-vietocr-v1/"
                    "frozen/crops/sample-00000001.png"
                ),
                "crop_sha256": "3" * 64,
                "sample_id": "sample-00000001",
            },
            {
                "category": "FULL_DOCUMENT_AUTHENTICATED_LINE",
                "crop_path": (
                    "output/development/loan-maturity-full-document-vietocr-v1/"
                    "frozen/crops/sample-00000002.png"
                ),
                "crop_sha256": "4" * 64,
                "sample_id": "sample-00000002",
            },
        ],
        "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
    }


def _result() -> dict[str, object]:
    samples = []
    for index, request_sample in enumerate(_request()["samples"]):
        samples.append(
            {
                **request_sample,
                "mean_decoded_character_probability": 0.9,
                "processed_height": 32,
                "processed_width": 100,
                # The empty second prediction is deliberately retained.
                "raw_prediction": "Nợ ngắn hạn" if index == 0 else "",
                "wall_seconds": 0.01,
            }
        )
    return {
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "experiment_id": "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1",
        "format_version": 2,
        "reference_text_available_to_reader": False,
        "sample_count": 2,
        "samples": samples,
        "state": "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE",
    }


def test_anonymous_request_has_only_opaque_ordered_samples() -> None:
    samples = builder.validate_anonymous_reader_request_v1(_request())

    assert [sample["sample_id"] for sample in samples] == [
        "sample-00000001",
        "sample-00000002",
    ]
    assert all(set(sample) == builder._REQUEST_SAMPLE_FIELDS for sample in samples)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: value["samples"][0].__setitem__("bank_code", "MBB"),
        lambda value: value["samples"][0].__setitem__("sample_id", "page-0031-line-0094"),
        lambda value: value["samples"][0].__setitem__(
            "crop_path", "output/MBB/page-0031/sample-00000001.png"
        ),
        lambda value: value["samples"].reverse(),
        lambda value: value.__setitem__("sample_count", 1),
    ],
)
def test_anonymous_request_rejects_identity_order_and_leak_tampering(tamper) -> None:
    request = copy.deepcopy(_request())
    tamper(request)

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error):
        builder.validate_anonymous_reader_request_v1(request)


def test_completed_result_preserves_empty_predictions_and_exact_order() -> None:
    samples = builder._validate_completed_vietocr_result_v1(_request(), _result())

    assert len(samples) == 2
    assert samples[0]["raw_prediction"] == "Nợ ngắn hạn"
    assert samples[1]["raw_prediction"] == ""


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: value["samples"].reverse(),
        lambda value: value["samples"].pop(),
        lambda value: value["samples"][0].__setitem__("normalized_prediction", "no ngan han"),
        lambda value: value["samples"][0].__setitem__("raw_prediction", None),
    ],
)
def test_completed_result_rejects_drop_reorder_or_postcorrection(tamper) -> None:
    result = copy.deepcopy(_result())
    tamper(result)

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error):
        builder._validate_completed_vietocr_result_v1(_request(), result)


def test_builder_pins_vietocr_vgg_transformer_0_3_13() -> None:
    reader = builder._validate_vietocr_transformer_config()

    assert reader == {
        "architecture": "vgg19_bn_transformer",
        "config_ref": {
            "path": "config/models/vietocr-0.3.13-rtx4090.toml",
            "sha256": "aa007448e2ed4f940693c3b4c03ae47111cf1ed00580d13c05a41941e5094119",
            "size_bytes": 2342,
        },
        "model_name": "VietOCR VGG Transformer",
        "package_version": "0.3.13",
        "weights_sha256": ("380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59"),
    }


def test_builder_never_reads_legacy_recognition_fields() -> None:
    source = Path(builder.__file__).read_text(encoding="utf-8")

    for forbidden in (
        'get("rec_texts")',
        '["rec_texts"]',
        'get("rec_boxes")',
        '["rec_boxes"]',
        'line.get("text")',
        'line["text"]',
        'line.get("source_text")',
        'line["source_text"]',
    ):
        assert forbidden not in source
    assert "replay_authenticated_line_pixel_hydration_v1" in source
    assert "_native_pixel_box" not in source


def test_builder_refuses_existing_fixed_output_before_reading_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / builder.OUTPUT_ROOT
    output.mkdir(parents=True)
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "_git", lambda *_args: "" if _args[0] == "status" else "0" * 40)

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error, match="refusing to overwrite"):
        builder.build_full_document_request_v1()


def test_content_ref_detects_byte_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"exact")
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    reference = {
        "path": "artifact.bin",
        "sha256": "fa79d4746c21cd960a17b92db8976ddef95a7e20b590721f8e0fa7847a05e486",
        "size_bytes": 5,
    }

    assert builder._verify_repository_content_ref(reference, "fixture") == b"exact"
    path.write_bytes(b"tampered")
    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error, match="bytes drifted"):
        builder._verify_repository_content_ref(reference, "fixture")


def test_directory_publication_is_atomic_and_never_overwrites(tmp_path: Path) -> None:
    first = tmp_path / "first-stage"
    first.mkdir()
    (first / "identity").write_text("first", encoding="utf-8")
    destination = tmp_path / "fixed-output"

    builder._publish_directory_noreplace(first, destination)

    assert not first.exists()
    assert (destination / "identity").read_text(encoding="utf-8") == "first"
    second = tmp_path / "second-stage"
    second.mkdir()
    (second / "identity").write_text("second", encoding="utf-8")
    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error, match="refusing to overwrite"):
        builder._publish_directory_noreplace(second, destination)
    assert (destination / "identity").read_text(encoding="utf-8") == "first"
    assert (second / "identity").read_text(encoding="utf-8") == "second"
