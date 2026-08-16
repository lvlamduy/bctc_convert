from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.experiments import build_loan_maturity_full_document_vietocr_request_v1 as builder


def _terminal_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    transcript_values: list[object] | None = None,
) -> dict[str, object]:
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "V3_ROOT", Path("sealed-v3"))
    buffer = io.BytesIO()
    Image.new("RGB", (100, 80), "white").save(buffer, format="PNG")
    render_raw = buffer.getvalue()
    render_relative = Path("objects/sha256/render.png")
    render_path = tmp_path / builder.V3_ROOT / render_relative
    render_path.parent.mkdir(parents=True)
    render_path.write_bytes(render_raw)
    render_ref = {
        "path": render_relative.as_posix(),
        "sha256": hashlib.sha256(render_raw).hexdigest(),
        "size_bytes": len(render_raw),
    }
    result_ref = {
        "path": "objects/sha256/result.json",
        "sha256": "1" * 64,
        "size_bytes": 101,
    }
    backend_ref = {
        "path": "objects/sha256/backend.json",
        "sha256": "2" * 64,
        "size_bytes": 202,
    }
    source_sha256 = "3" * 64
    request = {
        "provider_identity_sha256": "4" * 64,
        "render_runtime_identity_sha256": "5" * 64,
    }
    request_sha256 = "6" * 64
    raw_provider_payload = {
        "rec_boxes": [[2, 3, 20, 12], [30, 20, 70, 36]],
        "rec_polys": [
            [[2, 3], [20, 3], [20, 12], [2, 12]],
            [[30, 20], [70, 20], [70, 36], [30, 36]],
        ],
        # These deliberately adversarial legacy values are opaque to the adapter.
        "rec_texts": transcript_values if transcript_values is not None else ["", "POISON"],
        "text_word": {"must": "remain quarantined"},
        "text_word_boxes": None,
    }
    failure = {
        "control_identity_sha256": "7" * 64,
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "normalization_producer_implementation_ledger_sha256": "8" * 64,
        "pixel_dimensions": [100, 80],
        "policy_sha256": "9" * 64,
        "raw_payload_sha256": builder.canonical_json_sha256_v1(raw_provider_payload),
        "reason": builder._TERMINAL_FAILURE_REASON,
        "status": builder._TERMINAL_STATUS,
    }
    page_record = {
        "backend_payload_ref": backend_ref,
        "document_id": f"sha256:{source_sha256}",
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        "line_axis_count": 0,
        "physical_page": 7,
        "render_ref": render_ref,
        "request": request,
        "request_sha256": request_sha256,
        "result_ref": result_ref,
        "route": builder._RASTER_ROUTE,
        "source_sha256": source_sha256,
        "source_size_bytes": 303,
        "status": builder._TERMINAL_STATUS,
        "unresolved": True,
        "word_token_count": 0,
    }
    result = {
        "backend_payload_ref": backend_ref,
        "claim_boundary": "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY",
        "coordinate_authority": {"pixel_dimensions": [100, 80]},
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
        "input_render_ref": render_ref,
        "lines": [],
        "metrics": {"line_count": 0, "word_token_count": 0},
        "normalization_failure": copy.deepcopy(failure),
        "ocr_fallback_used": False,
        "physical_page": 7,
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_runtime_identity_sha256": request["render_runtime_identity_sha256"],
        "request": request,
        "request_sha256": request_sha256,
        "route": builder._RASTER_ROUTE,
        "safety": {key: False for key in builder._TERMINAL_RESULT_SAFETY_FIELDS},
        "source_blank_claimed": False,
        "source_sha256": source_sha256,
        "source_size_bytes": 303,
        "status": builder._TERMINAL_STATUS,
        "words": [],
    }
    backend = {
        "claim_boundary": (
            "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        ),
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3",
        "normalization_failure": failure,
        "provider_identity_sha256": request["provider_identity_sha256"],
        "raw_provider_payload": raw_provider_payload,
        "render_ref": render_ref,
        "request": request,
        "request_sha256": request_sha256,
        "word_box_normalization_ledger": None,
    }
    return {
        "backend": backend,
        "backend_ref": backend_ref,
        "page_record": page_record,
        "physical_page": 7,
        "result": result,
        "result_ref": result_ref,
        "source_sha256": source_sha256,
    }


def _refresh_terminal_failure(payload: dict[str, object]) -> None:
    backend = payload["backend"]
    result = payload["result"]
    assert isinstance(backend, dict)
    assert isinstance(result, dict)
    raw = backend["raw_provider_payload"]
    failure = backend["normalization_failure"]
    assert isinstance(failure, dict)
    failure["raw_payload_sha256"] = builder.canonical_json_sha256_v1(raw)
    result["normalization_failure"] = copy.deepcopy(failure)


def _run_terminal_fixture(payload: dict[str, object]):
    return builder._terminal_geometry_supplement_page(
        source_sha256=payload["source_sha256"],
        physical_page=payload["physical_page"],
        page_record=payload["page_record"],
        result=payload["result"],
        result_ref=payload["result_ref"],
        backend=payload["backend"],
        backend_ref=payload["backend_ref"],
    )


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


def _annual_provider_payload(*, text: str = "legacy text") -> dict[str, object]:
    return {
        "rec_texts": [text, ""],
        "rec_scores": [0.99, 0.95],
        "rec_polys": [
            [[2, 3], [20, 3], [20, 12], [2, 12]],
            [[30, 20], [70, 20], [70, 36], [30, 36]],
        ],
        "rec_boxes": [[2, 3, 20, 12], [30, 20, 70, 36]],
        "text_word_boxes": [[], []],
        "text_word": [[], []],
        "return_word_box": True,
    }


def test_annual_2025_profile_locks_exact_eight_source_denominator() -> None:
    assert [item["bank_code"] for item in builder.ANNUAL_2025_SOURCES] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_count"] for item in builder.ANNUAL_2025_SOURCES] == [
        100,
        103,
        100,
        71,
        84,
        85,
        74,
        78,
    ]
    assert sum(item["page_count"] for item in builder.ANNUAL_2025_SOURCES) == 695
    assert len({item["sha256"] for item in builder.ANNUAL_2025_SOURCES}) == 8


def test_annual_provider_geometry_is_transcript_independent() -> None:
    first = builder._annual_ppocr_line_boxes(
        _annual_provider_payload(text="poison"), width=100, height=80
    )
    second = builder._annual_ppocr_line_boxes(
        _annual_provider_payload(text="completely different"), width=100, height=80
    )

    assert first == second == [[2, 3, 20, 12], [30, 20, 70, 36]]


@pytest.mark.parametrize(
    "bad_box",
    (
        [2.0, 3, 20, 12],
        [2, 3, 101, 12],
        [2, 3, 2, 12],
        [True, 3, 20, 12],
    ),
)
def test_annual_provider_geometry_rejects_non_exact_or_invalid_boxes(bad_box) -> None:
    payload = _annual_provider_payload()
    payload["rec_boxes"][0] = bad_box

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error):
        builder._annual_ppocr_line_boxes(payload, width=100, height=80)


def test_annual_profile_reuses_fixed_blind_reader_paths() -> None:
    builder._activate_profile("annual-2025")
    try:
        assert builder.OUTPUT_ROOT == builder.ANNUAL_2025_OUTPUT_ROOT
        assert builder.VIETOCR_OUTPUT_DIRECTORY == (
            builder.ANNUAL_2025_OUTPUT_ROOT / "vietocr-transformer"
        )
        assert builder.VERIFIED_INDEX_DIRECTORY == (
            builder.ANNUAL_2025_OUTPUT_ROOT / "verified-index"
        )
    finally:
        builder._activate_profile("wave1")


def test_annual_page_geometry_binds_render_result_run_and_hides_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    render_path = tmp_path / "renders/page-0001.png"
    render_path.parent.mkdir(parents=True)
    render_buffer = io.BytesIO()
    Image.new("RGB", (100, 80), "white").save(render_buffer, format="PNG")
    render_raw = render_buffer.getvalue()
    render_path.write_bytes(render_raw)

    batch_root = tmp_path / "ppocr/ACB"
    result_path = batch_root / "ppocrv6-page-0001/ocr_result.json"
    run_path = batch_root / "ppocrv6-page-0001/run_manifest.json"
    result_path.parent.mkdir(parents=True)
    result_raw = json.dumps(_annual_provider_payload(text="MUST_NOT_LEAK")).encode()
    result_path.write_bytes(result_raw)
    render_record = {
        "dpi": 200,
        "height_pixels": 80,
        "page": 1,
        "path": "renders/page-0001.png",
        "sha256": hashlib.sha256(render_raw).hexdigest(),
        "size_bytes": len(render_raw),
        "width_pixels": 100,
    }
    metrics = {"line_count": 2}
    batch = {
        "batch_identity": "1" * 64,
        "code": {"commit": "2" * 40, "dirty": False},
        "configuration": {"precision": "fp32"},
        "runtime_identity": {"device": "cpu"},
    }
    run = {
        "artifacts": {
            "ocr_result": {
                "path": "ocr_result.json",
                "sha256": hashlib.sha256(result_raw).hexdigest(),
                "size_bytes": len(result_raw),
            }
        },
        "batch_identity": batch["batch_identity"],
        "code": batch["code"],
        "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
        "configuration": batch["configuration"],
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
        "input": render_record,
        "metrics": metrics,
        "page": 1,
        "runtime": batch["runtime_identity"],
        "schema_version": 1,
        "state": "OCR_COMPLETE",
    }
    run_raw = json.dumps(run).encode()
    run_path.write_bytes(run_raw)
    batch_page = {
        "metrics": metrics,
        "page": 1,
        "ocr_result": {
            "path": "ppocrv6-page-0001/ocr_result.json",
            "sha256": hashlib.sha256(result_raw).hexdigest(),
            "size_bytes": len(result_raw),
        },
        "run_manifest": {
            "path": "ppocrv6-page-0001/run_manifest.json",
            "sha256": hashlib.sha256(run_raw).hexdigest(),
            "size_bytes": len(run_raw),
        },
    }

    _render, boxes, render_ref, projection, result_ref, run_ref = builder._annual_page_geometry(
        bank="ACB",
        batch_root=batch_root,
        batch=batch,
        batch_page=batch_page,
        render_record=render_record,
        physical_page=1,
    )

    assert boxes == [[2, 3, 20, 12], [30, 20, 70, 36]]
    assert render_ref["path"] == "renders/page-0001.png"
    assert result_ref["path"] == "ppocr/ACB/ppocrv6-page-0001/ocr_result.json"
    assert run_ref["path"] == "ppocr/ACB/ppocrv6-page-0001/run_manifest.json"
    assert projection["mode"] == "PPOCRV6_BATCH_PROVIDER_LINE_GEOMETRY_V1"
    assert "MUST_NOT_LEAK" not in json.dumps(projection, sort_keys=True)


def test_builder_never_reads_legacy_recognition_fields() -> None:
    source = Path(builder.__file__).read_text(encoding="utf-8")

    for forbidden in (
        'get("rec_texts")',
        '["rec_texts"]',
        'get("text_word")',
        '["text_word"]',
        'get("text_word_boxes")',
        '["text_word_boxes"]',
        'line.get("text")',
        'line["text"]',
        'line.get("source_text")',
        'line["source_text"]',
    ):
        assert forbidden not in source
    assert "replay_authenticated_line_pixel_hydration_v1" in source
    assert "_native_pixel_box" not in source

    terminal_source = inspect.getsource(builder._terminal_geometry_supplement_page)
    assert 'get("rec_boxes")' in terminal_source
    assert 'get("rec_polys")' in terminal_source
    assert "replay_authenticated_line_pixel_hydration_v1" not in terminal_source
    forbidden_terminal_axes = {"rec_texts", "text_word", "text_word_boxes"}
    for node in ast.walk(ast.parse(terminal_source)):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            assert node.slice.value not in forbidden_terminal_axes
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
            assert node.args[0].value not in forbidden_terminal_axes


def test_terminal_supplement_preserves_every_geometry_and_quarantines_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _terminal_fixture(tmp_path, monkeypatch)

    _render, boxes, render_binding, projection, receipt = _run_terminal_fixture(payload)

    assert boxes == [[2, 3, 20, 12], [30, 20, 70, 36]]
    assert render_binding["path"] == "sealed-v3/objects/sha256/render.png"
    assert projection["mode"] == "TERMINAL_EXPERIMENT_LOCAL_PROVIDER_LINE_GEOMETRY_ONLY_V1"
    assert projection["provider_geometry_denominator"] == 2
    assert (
        projection["sha256"] == hashlib.sha256(builder.canonical_json_bytes_v1(receipt)).hexdigest()
    )
    assert receipt["source_binding"] == {
        "backend_ref": {
            "path": "sealed-v3/objects/sha256/backend.json",
            "sha256": "2" * 64,
            "size_bytes": 202,
        },
        "physical_page": 7,
        "render_ref": render_binding,
        "result_ref": {
            "path": "sealed-v3/objects/sha256/result.json",
            "sha256": "1" * 64,
            "size_bytes": 101,
        },
        "source_pdf_sha256": "3" * 64,
        "v3_page_record_sha256": builder.canonical_json_sha256_v1(payload["page_record"]),
    }
    assert receipt["terminal_state"] == {
        "public_line_axis_count": 0,
        "route": builder._RASTER_ROUTE,
        "status": builder._TERMINAL_STATUS,
        "status_preserved": True,
        "unresolved": True,
    }
    assert receipt["quarantine"] == {
        "provider_recognition_text_exposed": False,
        "provider_recognition_text_used_for_selection": False,
        "word_geometry_exposed": False,
        "word_text_exposed": False,
    }
    serialized_receipt = json.dumps(receipt, sort_keys=True)
    assert "POISON" not in serialized_receipt
    assert "remain quarantined" not in serialized_receipt


def test_terminal_supplement_geometry_is_independent_of_legacy_transcript_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _terminal_fixture(
        tmp_path / "first",
        monkeypatch,
        transcript_values=["", "arbitrary legacy bytes"],
    )
    first_output = _run_terminal_fixture(first)
    second = _terminal_fixture(
        tmp_path / "second",
        monkeypatch,
        transcript_values=[{"unexpected": "shape"}],
    )
    second_output = _run_terminal_fixture(second)

    assert first_output[1] == second_output[1]
    assert first_output[3]["provider_geometry_denominator"] == 2
    assert second_output[3]["provider_geometry_denominator"] == 2
    assert first_output[3]["geometry_axis_sha256"] == second_output[3]["geometry_axis_sha256"]
    assert (
        first_output[4]["upstream_raw_provider_payload_sha256"]
        != second_output[4]["upstream_raw_provider_payload_sha256"]
    )


def test_terminal_supplement_preserves_provider_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _terminal_fixture(tmp_path / "original", monkeypatch)
    original_output = _run_terminal_fixture(original)
    reordered = _terminal_fixture(tmp_path / "reordered", monkeypatch)
    backend = reordered["backend"]
    assert isinstance(backend, dict)
    raw = backend["raw_provider_payload"]
    assert isinstance(raw, dict)
    raw["rec_boxes"].reverse()
    raw["rec_polys"].reverse()
    _refresh_terminal_failure(reordered)

    reordered_output = _run_terminal_fixture(reordered)

    assert reordered_output[1] == list(reversed(original_output[1]))
    assert reordered_output[3]["geometry_axis_sha256"] != original_output[3]["geometry_axis_sha256"]


def test_terminal_supplement_rejects_raw_payload_hash_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _terminal_fixture(tmp_path, monkeypatch)
    backend = payload["backend"]
    assert isinstance(backend, dict)
    raw = backend["raw_provider_payload"]
    assert isinstance(raw, dict)
    raw["opaque_tamper"] = True

    with pytest.raises(
        builder.FullDocumentVietOCRRequestV1Error,
        match="backend/result/failure binding",
    ):
        _run_terminal_fixture(payload)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        (
            lambda raw: raw["rec_polys"].pop(),
            "geometry denominator",
        ),
        (
            lambda raw: raw["rec_boxes"][0].__setitem__(2, 101),
            "bbox lies outside render",
        ),
        (
            lambda raw: raw["rec_polys"].__setitem__(0, [[2, 3], [3, 3], [4, 3], [5, 3]]),
            "degenerate",
        ),
        (
            lambda raw: raw["rec_polys"][0].__setitem__(0, [0, 0]),
            "outside its provider line bbox",
        ),
        (
            lambda raw: raw["rec_polys"][0][0].__setitem__(0, 2.0),
            "exact integer quadrilateral",
        ),
    ],
)
def test_terminal_supplement_rejects_geometry_axis_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper,
    message: str,
) -> None:
    payload = _terminal_fixture(tmp_path, monkeypatch)
    backend = payload["backend"]
    assert isinstance(backend, dict)
    raw = backend["raw_provider_payload"]
    assert isinstance(raw, dict)
    tamper(raw)
    _refresh_terminal_failure(payload)

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error, match=message):
        _run_terminal_fixture(payload)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda payload: payload["page_record"].__setitem__("unresolved", False),
        lambda payload: payload["page_record"].__setitem__("line_axis_count", 1),
        lambda payload: payload["result"].__setitem__("status", builder._RASTER_STATUS),
        lambda payload: payload.__setitem__(
            "backend_ref", {**payload["backend_ref"], "sha256": "a" * 64}
        ),
    ],
)
def test_terminal_supplement_rejects_state_and_reference_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper,
) -> None:
    payload = _terminal_fixture(tmp_path, monkeypatch)
    tamper(payload)

    with pytest.raises(builder.FullDocumentVietOCRRequestV1Error):
        _run_terminal_fixture(payload)


def test_exact_vcb_terminal_geometry_denominator_and_order() -> None:
    vcb_sha256 = "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"
    document, _document_raw = builder._json(
        builder.PROJECT_ROOT / builder.V3_ROOT / "documents" / f"{vcb_sha256}.json",
        "VCB V3 document fixture",
    )
    expected_counts = {1: 57, 16: 49, 31: 91, 38: 77, 41: 67}
    expected_geometry_hashes = {
        1: "e9b041194dfd031d2985d1b0194a198c303ec81ce30408765f3b045095fe6d2e",
        16: "b896c784d0026100bbd93eef83de2bdb4b8dbe5d45196fb9413181923d39a412",
        31: "174c83c145c74e77ef073b6d808ce1adcc9134c5e3e27a17e51815a184096c66",
        38: "ee0ec808f32a99679b481d74133353fb735effc0637807a79f9f882ebe58208a",
        41: "187aecacb4a06503a161f448a13715d9d477ca29665af55104fc4e900eba0da6",
    }
    actual_counts: dict[int, int] = {}
    geometry_hashes: dict[int, str] = {}
    for page_record in document["page_records"]:
        if page_record.get("status") != builder._TERMINAL_STATUS:
            continue
        physical_page = page_record["physical_page"]
        _result_path, result_raw, result_ref = builder._verified_ref(
            builder.PROJECT_ROOT / builder.V3_ROOT,
            page_record["result_ref"],
            f"VCB terminal result {physical_page}",
        )
        _backend_path, backend_raw, backend_ref = builder._verified_ref(
            builder.PROJECT_ROOT / builder.V3_ROOT,
            page_record["backend_payload_ref"],
            f"VCB terminal backend {physical_page}",
        )
        result = builder._decode_json(result_raw, f"VCB terminal result {physical_page}")
        backend = builder._decode_json(backend_raw, f"VCB terminal backend {physical_page}")

        _render, boxes, _render_binding, projection, receipt = (
            builder._terminal_geometry_supplement_page(
                source_sha256=vcb_sha256,
                physical_page=physical_page,
                page_record=page_record,
                result=result,
                result_ref=result_ref,
                backend=backend,
                backend_ref=backend_ref,
            )
        )

        actual_counts[physical_page] = len(boxes)
        geometry_hashes[physical_page] = projection["geometry_axis_sha256"]
        assert receipt["terminal_state"]["status_preserved"] is True
        assert receipt["terminal_state"]["unresolved"] is True
        assert not any(receipt["quarantine"].values())

    assert actual_counts == expected_counts
    assert sum(actual_counts.values()) == 341
    assert geometry_hashes == expected_geometry_hashes


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
