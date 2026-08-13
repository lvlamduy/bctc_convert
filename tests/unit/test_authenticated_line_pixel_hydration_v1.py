from __future__ import annotations

import copy
import hashlib
import inspect
import pickle
from pathlib import Path
from typing import Any, cast

import fitz
import pytest

import bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 as hydration
from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    ENVELOPE_FORMAT_VERSION,
    RECEIPT_FORMAT_VERSION,
    AuthenticatedLinePixelHydrationReceiptV1,
    AuthenticatedLinePixelHydrationV1Error,
    project_authenticated_line_pixel_hydration_receipt_v1,
    read_authenticated_line_pixel_hydration_envelope_v1,
    read_authenticated_line_pixel_hydration_render_v1,
    replay_authenticated_line_pixel_hydration_v1,
    validate_authenticated_line_pixel_hydration_envelope_v1,
    validate_line_pixel_hydration_envelope_v1,
)
from bctc_ai.rendering.page_reader import coordinate_authority, public_coordinate_authority
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT_ROOT / "src/bctc_ai/evaluation/authenticated_line_pixel_hydration_v1.py"


def _sha(character: str) -> str:
    return character * 64


def _ref(character: str, suffix: str = ".json") -> dict[str, Any]:
    digest = _sha(character)
    return {
        "path": f"objects/sha256/{digest[:2]}/{digest}{suffix}",
        "sha256": digest,
        "size_bytes": 1,
    }


def _coordinate_authority() -> dict[str, Any]:
    document = fitz.open()
    try:
        page = document.new_page(width=72, height=72)
        return public_coordinate_authority(
            coordinate_authority(page, pixel_width=100, pixel_height=100)
        )
    finally:
        document.close()


def _envelope() -> dict[str, Any]:
    pins = FINALIZED_V3_SURVEY_AUTHORITY_V1
    envelope = {
        "format_version": ENVELOPE_FORMAT_VERSION,
        "claim_boundary": hydration._CLAIM_BOUNDARY,
        "envelope_id": hydration._ENVELOPE_ID_PREFIX + "0" * 64,
        "adapter_id": hydration._NATIVE_ADAPTER_ID,
        "source_state": hydration._source_state_payload(hydration._NATIVE_STATE),
        "finalized_v3_authority": {
            "aggregate_artifact_ref": {
                "sha256": pins.aggregate_artifact_sha256,
                "size_bytes": pins.aggregate_size_bytes,
            },
            "aggregate_identity_sha256": pins.aggregate_identity_sha256,
            "control_artifact_ref": {
                "sha256": pins.control_artifact_sha256,
                "size_bytes": pins.control_size_bytes,
            },
            "control_identity_sha256": pins.control_identity_sha256,
            "document_count": pins.document_count,
            "request_count": pins.request_count,
            "sealed_plan_ref": {
                "sha256": pins.sealed_plan_sha256,
                "size_bytes": hydration.sentinel.SEALED_PLAN_SIZE_BYTES,
            },
        },
        "source_binding": {
            "document_id": f"sha256:{_sha('a')}",
            "physical_page": 1,
            "plan_document_binding_sha256": _sha("b"),
            "plan_page_binding_sha256": _sha("c"),
            "request_sha256": _sha("d"),
            "source_pdf_sha256": _sha("a"),
            "source_size_bytes": 1,
        },
        "upstream_binding": {
            "backend_payload_ref": _ref("e"),
            "line_text_axis_sha256": _sha("f"),
            "page_record_format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
            "page_record_sha256": _sha("1"),
            "raw_provider_payload_sha256": None,
            "render_ref": None,
            "request_ordinal": 1,
            "result_format_version": hydration._NATIVE_RESULT_FORMAT,
            "result_ref": _ref("2"),
            "route": hydration._NATIVE_ROUTE,
            "status": hydration._NATIVE_STATUS,
            "status_preserved": True,
            "unresolved": False,
        },
        "render_binding": {
            "dpi": 200,
            "origin": "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY",
            "pixel_height": 100,
            "pixel_width": 100,
            "render_profile": {
                "alpha": False,
                "annotations": "INCLUDED",
                "colorspace": "RGB",
                "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
            },
            "sha256": hashlib.sha256(b"r").hexdigest(),
            "size_bytes": 1,
            "upstream_render_ref": None,
        },
        "coordinate_authority": _coordinate_authority(),
        "lines": [
            {
                "canonical_bbox_mpt": [720, 720, 1440, 1440],
                "line_index": 0,
                "raw_pixel_bbox": [1, 1, 2, 2],
                "source_geometry_sha256": _sha("4"),
            }
        ],
        "metrics": {
            "authenticated_source_line_axis_count": 1,
            "emitted_line_count": 1,
            "excluded_line_count": 0,
            "upstream_public_line_axis_count": 1,
        },
        "quarantine": {
            "source_word_axis_count": 0,
            "terminal_word_geometry_failure_preserved": False,
            "word_axis_sha256": _sha("5"),
            "word_geometry_exposed": False,
            "word_text_exposed": False,
        },
        "authority": copy.deepcopy(hydration._AUTHORITY),
    }
    envelope["envelope_id"] = hydration._ENVELOPE_ID_PREFIX + canonical_json_sha256_v1(
        {key: value for key, value in envelope.items() if key != "envelope_id"}
    )
    return envelope


def _terminal_raw() -> dict[str, Any]:
    return {
        "dt_polys": [],
        "model_settings": {},
        "page_index": 0,
        "return_word_box": True,
        "rec_texts": ["one line"],
        "rec_scores": [0.9],
        "rec_polys": [[[1, 1], [9, 1], [9, 9], [1, 9]]],
        "rec_boxes": [[1, 1, 9, 9]],
        # This deliberately lies outside the line/page.  Only word geometry is
        # replaced for the structural validation; it remains quarantined.
        "text_word_boxes": [[[-2, 2, 3, 5]]],
        "text_word": [["one"]],
        "text_det_params": {},
        "text_rec_score_thresh": 0.0,
        "text_type": "general",
        "textline_orientation_angles": [],
    }


def test_public_replay_selector_is_reference_blind_and_has_exact_types() -> None:
    signature = inspect.signature(replay_authenticated_line_pixel_hydration_v1)
    assert tuple(signature.parameters) == (
        "project_root",
        "source_pdf_sha256",
        "physical_page",
    )
    assert signature.parameters["source_pdf_sha256"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["physical_page"].kind is inspect.Parameter.KEYWORD_ONLY

    for root, digest, page, message in (
        (cast(Any, "."), _sha("a"), 1, "pathlib Path"),
        (PROJECT_ROOT, cast(Any, b"a" * 64), 1, "SHA-256 string"),
        (PROJECT_ROOT, "A" * 64, 1, "lowercase SHA-256"),
        (PROJECT_ROOT, _sha("a"), cast(Any, True), "positive integer"),
        (PROJECT_ROOT, _sha("a"), 0, "positive integer"),
    ):
        with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match=message):
            replay_authenticated_line_pixel_hydration_v1(
                root, source_pdf_sha256=digest, physical_page=page
            )


def test_source_state_tuple_routes_only_two_closed_generic_adapters() -> None:
    assert hydration._adapter_for_source_state(hydration._NATIVE_STATE) == (
        hydration._NATIVE_ADAPTER_ID
    )
    assert hydration._adapter_for_source_state(hydration._TERMINAL_STATE) == (
        hydration._TERMINAL_ADAPTER_ID
    )
    for index, replacement in (
        (1, "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"),
        (3, hydration._OCR_TERMINAL_STATUS),
        (4, "RENDER_PRESENT"),
        (5, "ZERO_PUBLIC_LINE_DENOMINATOR"),
        (6, True),
        (6, 0),
    ):
        changed = list(hydration._NATIVE_STATE)
        changed[index] = replacement
        with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="no admitted"):
            hydration._adapter_for_source_state(tuple(changed))


def test_closed_envelope_mints_live_uncopyable_capability_and_receipt() -> None:
    envelope = validate_line_pixel_hydration_envelope_v1(_envelope())
    capability = hydration._mint(envelope, b"r")

    assert isinstance(capability, AuthenticatedLinePixelHydrationReceiptV1)
    assert read_authenticated_line_pixel_hydration_envelope_v1(capability) == envelope
    assert read_authenticated_line_pixel_hydration_render_v1(capability) == b"r"
    receipt = project_authenticated_line_pixel_hydration_receipt_v1(capability)
    assert receipt["format_version"] == RECEIPT_FORMAT_VERSION
    assert receipt["adapter_id"] == hydration._NATIVE_ADAPTER_ID
    assert receipt["emitted_line_count"] == 1
    assert receipt["upstream_status"] == hydration._NATIVE_STATUS
    assert receipt["authority"] == hydration._RECEIPT_AUTHORITY
    assert validate_authenticated_line_pixel_hydration_envelope_v1(envelope, capability) == envelope

    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(AuthenticatedLinePixelHydrationV1Error):
            operation(capability)
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="caller-constructed"):
        AuthenticatedLinePixelHydrationReceiptV1(object())
    forged = object.__new__(AuthenticatedLinePixelHydrationReceiptV1)
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="unknown or expired"):
        project_authenticated_line_pixel_hydration_receipt_v1(forged)
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="exact opaque"):
        project_authenticated_line_pixel_hydration_receipt_v1(cast(Any, envelope))

    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="render bytes differ"):
        hydration._mint(envelope, b"x")
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="render bytes differ"):
        hydration._mint(envelope, b"rr")
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="render bytes differ"):
        hydration._mint(envelope, cast(Any, bytearray(b"r")))


def test_coordinated_self_rehash_does_not_cross_live_capability_boundary() -> None:
    envelope = _envelope()
    capability = hydration._mint(envelope, b"r")
    tampered = copy.deepcopy(envelope)
    tampered["lines"][0]["raw_pixel_bbox"] = [2, 2, 3, 3]
    tampered["envelope_id"] = hydration._ENVELOPE_ID_PREFIX + canonical_json_sha256_v1(
        {key: value for key, value in tampered.items() if key != "envelope_id"}
    )

    assert validate_line_pixel_hydration_envelope_v1(tampered) == tampered
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="differs from live"):
        validate_authenticated_line_pixel_hydration_envelope_v1(tampered, capability)


@pytest.mark.parametrize(
    ("container", "field"),
    (("source_state", "unresolved"), ("upstream_binding", "unresolved")),
)
def test_integer_zero_cannot_substitute_for_exact_boolean(container: str, field: str) -> None:
    envelope = _envelope()
    envelope[container][field] = 0
    envelope["envelope_id"] = hydration._ENVELOPE_ID_PREFIX + canonical_json_sha256_v1(
        {key: value for key, value in envelope.items() if key != "envelope_id"}
    )
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="boolean"):
        validate_line_pixel_hydration_envelope_v1(envelope)


def test_terminal_provider_validation_preserves_full_lines_and_quarantines_words() -> None:
    raw = _terminal_raw()
    sanitized, text_hash, word_count, word_hash = hydration._terminal_raw_axes(
        raw, pixel_width=10, pixel_height=10
    )

    assert sanitized["text_word_boxes"] == [[[1, 1, 9, 9]]]
    assert raw["text_word_boxes"] == [[[-2, 2, 3, 5]]]
    assert text_hash == canonical_json_sha256_v1(["one line"])
    assert word_count == 1
    assert word_hash == canonical_json_sha256_v1([[raw["text_word"][0], raw["text_word_boxes"][0]]])

    empty = copy.deepcopy(raw)
    empty["rec_texts"] = [""]
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="full nonempty"):
        hydration._terminal_raw_axes(empty, pixel_width=10, pixel_height=10)
    misaligned = copy.deepcopy(raw)
    misaligned["rec_scores"] = []
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="misaligned"):
        hydration._terminal_raw_axes(misaligned, pixel_width=10, pixel_height=10)
    nonfinite = copy.deepcopy(raw)
    nonfinite["rec_scores"] = [float("nan")]
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="non-word-geometry"):
        hydration._terminal_raw_axes(nonfinite, pixel_width=10, pixel_height=10)
    extra = copy.deepcopy(raw)
    extra["foreign"] = None
    with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="non-word-geometry"):
        hydration._terminal_raw_axes(extra, pixel_width=10, pixel_height=10)


def test_native_outward_projection_is_positive_in_bounds_and_reverse_enclosing() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=72, height=72)
        authority = coordinate_authority(page, pixel_width=100, pixel_height=100)
        assert hydration._native_pixel_box(
            [1000, 1000, 10001, 10001],
            coordinate_authority=authority,
            pixel_width=100,
            pixel_height=100,
        ) == [1, 1, 14, 14]
        with pytest.raises(AuthenticatedLinePixelHydrationV1Error, match="outside"):
            hydration._native_pixel_box(
                [-1, 0, 1000, 1000],
                coordinate_authority=authority,
                pixel_width=100,
                pixel_height=100,
            )
    finally:
        document.close()


def test_static_finalized_v3_pins_and_source_are_bank_and_page_constant_free() -> None:
    pins = FINALIZED_V3_SURVEY_AUTHORITY_V1
    assert pins.aggregate_artifact_sha256 == (
        "b2b41986d4e534a3afe4799fb00462854e66f76b61e23cb36090c98aab53f0b3"
    )
    assert pins.aggregate_size_bytes == 6_796_775
    assert pins.control_artifact_sha256 == (
        "4d8e3206e6518c2e61104aa9cda6bcea310211fa2e5bec39c38b919abe4536e8"
    )
    assert pins.control_size_bytes == 2_401_205
    assert pins.sealed_plan_sha256 == (
        "d056323fde832ec2865ef5ac28a3fb045537ef6ecf3c505a7b5b0bbb68ad29c3"
    )
    assert pins.request_count == 1_449

    source = SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        '"VPB"',
        '"VCB"',
        "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde",
        "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223",
        "vietstock_bctc/",
    ):
        assert forbidden not in source
