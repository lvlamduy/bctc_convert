from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    ENVELOPE_FORMAT_VERSION,
    RECEIPT_FORMAT_VERSION,
    project_authenticated_line_pixel_hydration_receipt_v1,
    read_authenticated_line_pixel_hydration_render_v1,
    replay_authenticated_line_pixel_hydration_v1,
    validate_authenticated_line_pixel_hydration_envelope_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CASES = (
    {
        "label": "native-no-render",
        "source_pdf_sha256": ("614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"),
        "physical_page": 42,
        "adapter_id": "NATIVE_CANONICAL_MPT_TO_DETERMINISTIC_200_DPI_PIXEL_V1",
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "unresolved": False,
        "upstream_public_line_axis_count": 110,
        "emitted_line_count": 110,
        "source_word_axis_count": 295,
        "word_axis_sha256": ("1895e635986a767064ac18a36ab2b0028ccf97df7b41fed824b3dc91d1006037"),
        "terminal_word_geometry_failure_preserved": False,
        "render_sha256": ("cc6c66ad90a801380b011b4ca77543fa5b27feed417ceea72f7835a5e3d6e665"),
        "render_size_bytes": 307_767,
        "pixel_width": 1_700,
        "pixel_height": 2_200,
        "render_origin": "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY",
        "backend_sha256": ("5dcdf2f8b36ab5e258b78d8a5dfb048056ada433f02be8e39332de00803c71fc"),
        "result_sha256": ("eb22ccd4e2e212c888b6c7ca8eccecee3d5ccbd0035ef67ef7051aed5a5821d8"),
        "receipt_id": (
            "alpghv1:receipt:b13a08413d7255c98db10ff3b60c3f832d4e8b304ecea14d44c331ca0a6a8d47"
        ),
        "upstream_render": False,
    },
    {
        "label": "terminal-word-geometry",
        "source_pdf_sha256": ("fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"),
        "physical_page": 31,
        "adapter_id": "TERMINAL_PPOCRV6_LINE_GEOMETRY_WORD_QUARANTINE_V1",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "unresolved": True,
        "upstream_public_line_axis_count": 0,
        "emitted_line_count": 91,
        "source_word_axis_count": 621,
        "word_axis_sha256": ("ecaf41d5839e4a567ed8fcbda7376bfe4ded10d76d23013738d233cb46b159ef"),
        "terminal_word_geometry_failure_preserved": True,
        "render_sha256": ("46a6eb710fdfbfe3aff4fbe33e8295b2876eeff421b8eefd0ebcc4aa7830aedd"),
        "render_size_bytes": 1_025_602,
        "pixel_width": 1_643,
        "pixel_height": 2_344,
        "render_origin": "EXACT_UPSTREAM_RENDER_REPRODUCED_FROM_SOURCE",
        "backend_sha256": ("43c4b9812cdc01d4b8c479e34b83b931dc35a342dbe8f5ea25baa1c000da4dc6"),
        "result_sha256": ("610520a41c1a1474b3e060b37537fead86ca43b7035e6063dd25d2cb040780a9"),
        "receipt_id": (
            "alpghv1:receipt:fe4017d0f735390cd6c22155cf3d34fd3b5c8dad6bfb45270bb202819e1c477e"
        ),
        "upstream_render": True,
    },
)


def _run(case: dict[str, Any]) -> dict[str, Any]:
    envelope, capability = replay_authenticated_line_pixel_hydration_v1(
        PROJECT_ROOT,
        source_pdf_sha256=case["source_pdf_sha256"],
        physical_page=case["physical_page"],
    )
    return {
        "capability": capability,
        "envelope": envelope,
        "receipt": project_authenticated_line_pixel_hydration_receipt_v1(capability),
        "render": read_authenticated_line_pixel_hydration_render_v1(capability),
    }


@pytest.fixture(scope="module")
def replayed_twice() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    first = {case["label"]: _run(case) for case in _CASES}
    second = {case["label"]: _run(case) for case in _CASES}
    return {label: (first[label], second[label]) for label in first}


def _all_keys(value: Any) -> set[str]:
    if type(value) is dict:
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if type(value) is list:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["label"])
def test_public_replay_is_exact_geometry_only_and_deterministic(
    replayed_twice: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    case: dict[str, Any],
) -> None:
    first, second = replayed_twice[case["label"]]
    envelope = first["envelope"]
    receipt = first["receipt"]
    render = first["render"]

    assert envelope == second["envelope"]
    assert receipt == second["receipt"]
    assert render == second["render"]
    assert envelope["format_version"] == ENVELOPE_FORMAT_VERSION
    assert envelope["adapter_id"] == case["adapter_id"]
    assert envelope["source_binding"]["source_pdf_sha256"] == case["source_pdf_sha256"]
    assert envelope["source_binding"]["physical_page"] == case["physical_page"]
    assert envelope["upstream_binding"]["status"] == case["status"]
    assert envelope["upstream_binding"]["unresolved"] is case["unresolved"]
    assert envelope["upstream_binding"]["status_preserved"] is True
    assert envelope["upstream_binding"]["backend_payload_ref"]["sha256"] == (case["backend_sha256"])
    assert envelope["upstream_binding"]["result_ref"]["sha256"] == (case["result_sha256"])

    metrics = envelope["metrics"]
    assert metrics == {
        "authenticated_source_line_axis_count": case["emitted_line_count"],
        "emitted_line_count": case["emitted_line_count"],
        "excluded_line_count": 0,
        "upstream_public_line_axis_count": case["upstream_public_line_axis_count"],
    }
    lines = envelope["lines"]
    assert len(lines) == case["emitted_line_count"]
    assert [line["line_index"] for line in lines] == list(range(len(lines)))
    assert len({tuple(line["raw_pixel_bbox"]) for line in lines}) == len(lines)
    width = case["pixel_width"]
    height = case["pixel_height"]
    canonical_width, canonical_height = envelope["coordinate_authority"]["unrotated_dimensions_mpt"]
    for line in lines:
        x0, y0, x1, y1 = line["raw_pixel_bbox"]
        assert 0 <= x0 < x1 <= width
        assert 0 <= y0 < y1 <= height
        cx0, cy0, cx1, cy1 = line["canonical_bbox_mpt"]
        assert 0 <= cx0 < cx1 <= canonical_width
        assert 0 <= cy0 < cy1 <= canonical_height
        assert _SHA256.fullmatch(line["source_geometry_sha256"])

    render_binding = envelope["render_binding"]
    assert render_binding["dpi"] == 200
    assert render_binding["origin"] == case["render_origin"]
    assert render_binding["sha256"] == case["render_sha256"]
    assert render_binding["size_bytes"] == case["render_size_bytes"]
    assert render_binding["pixel_width"] == width
    assert render_binding["pixel_height"] == height
    assert len(render) == case["render_size_bytes"]
    assert hashlib.sha256(render).hexdigest() == case["render_sha256"]
    assert render.startswith(b"\x89PNG\r\n\x1a\n")
    if case["upstream_render"]:
        assert render_binding["upstream_render_ref"] == {
            "path": (f"objects/sha256/{case['render_sha256'][:2]}/{case['render_sha256']}.png"),
            "sha256": case["render_sha256"],
            "size_bytes": case["render_size_bytes"],
        }
    else:
        assert render_binding["upstream_render_ref"] is None

    assert envelope["quarantine"] == {
        "source_word_axis_count": case["source_word_axis_count"],
        "terminal_word_geometry_failure_preserved": case[
            "terminal_word_geometry_failure_preserved"
        ],
        "word_axis_sha256": case["word_axis_sha256"],
        "word_geometry_exposed": False,
        "word_text_exposed": False,
    }
    assert envelope["authority"]["geometry_only_authority"] is True
    assert envelope["authority"]["line_pixel_geometry_authority"] is True
    for false_claim in (
        "mapping_authority",
        "network_used",
        "numeric_authority",
        "ocr_model_invoked",
        "ppocr_transcript_semantic_authority",
        "recognition_authority",
        "schema_authority",
        "semantic_authority",
    ):
        assert envelope["authority"][false_claim] is False
    forbidden_evidence_keys = {
        "raw_text",
        "rec_scores",
        "rec_texts",
        "score",
        "text",
        "text_word",
        "text_word_boxes",
        "words",
    }
    assert not (_all_keys(envelope) & forbidden_evidence_keys)
    assert not (_all_keys(receipt) & forbidden_evidence_keys)

    assert receipt["format_version"] == RECEIPT_FORMAT_VERSION
    assert receipt["receipt_id"] == case["receipt_id"]
    assert receipt["adapter_id"] == case["adapter_id"]
    assert receipt["source_locator"] == {
        "physical_page": case["physical_page"],
        "source_pdf_sha256": case["source_pdf_sha256"],
        "source_size_bytes": envelope["source_binding"]["source_size_bytes"],
    }
    envelope_payload = canonical_json_bytes_v1(envelope)
    assert receipt["envelope_ref"] == {
        "sha256": hashlib.sha256(envelope_payload).hexdigest(),
        "size_bytes": len(envelope_payload),
    }
    assert receipt["render_ref"] == {
        "sha256": case["render_sha256"],
        "size_bytes": case["render_size_bytes"],
    }
    assert receipt["upstream_backend_ref"] == envelope["upstream_binding"]["backend_payload_ref"]
    assert receipt["upstream_result_ref"] == envelope["upstream_binding"]["result_ref"]
    assert receipt["upstream_status"] == case["status"]
    assert receipt["emitted_line_count"] == case["emitted_line_count"]
    assert receipt["line_axis_sha256"] == canonical_json_sha256_v1(lines)
    assert receipt["authority"] == {
        "geometry_only_authority": True,
        "live_capability_required": True,
        "raw_envelope_self_authenticates": False,
        "raw_receipt_self_authenticates": False,
        "recognition_authority": False,
        "semantic_or_numeric_authority": False,
    }
    assert (
        validate_authenticated_line_pixel_hydration_envelope_v1(envelope, first["capability"])
        == envelope
    )
