from __future__ import annotations

import copy
import json
from collections.abc import Callable
from hashlib import sha256
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

import fitz
import pytest

from bctc_ai.ocr.causal_native_text_evidence_v1 import (
    BACKEND_FORMAT_VERSION,
    RESULT_FORMAT_VERSION,
    CausalNativeTextEvidenceError,
    build_causal_native_text_evidence,
    validate_causal_native_text_evidence_replay,
)

_CAUSAL_POLICY = Path("config/ocr/causal-native-text-v1.yaml")
_QUALITY_POLICY = Path("config/ocr/native-text-quality-v2.yaml")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _provider_ledger(project_root: Path) -> dict[str, Any]:
    records = []
    for relative_path in (_CAUSAL_POLICY, _QUALITY_POLICY):
        payload = (project_root / relative_path).read_bytes()
        records.append(
            {
                "path": relative_path.as_posix(),
                "sha256": sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    ledger = {
        "config_records": records,
        "ocr_fallback_allowed": False,
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_distribution_version": distribution_version("PyMuPDF"),
        "pymupdf_runtime_versions": list(fitz.version),
    }
    ledger["sha256"] = sha256(_canonical_bytes(ledger)).hexdigest()
    return ledger


def _pdf_bytes(
    draw: Callable[[fitz.Page], None] | None = None,
    *,
    rotation: int = 0,
) -> bytes:
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    if draw is not None:
        draw(page)
    if rotation:
        page.set_rotation(rotation)
    payload = document.tobytes(garbage=4, deflate=True)
    document.close()
    return payload


def _arguments(
    project_root: Path,
    source_bytes: bytes,
    *,
    physical_page: int = 1,
) -> dict[str, Any]:
    ledger = _provider_ledger(project_root)
    source_sha256 = sha256(source_bytes).hexdigest()
    request = {
        "bank_identity_used": False,
        "filename_used": False,
        "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
        "git_commit": "a" * 40,
        "historical_values_used": False,
        "implementation_ledger_sha256": "b" * 64,
        "input_ledger_sha256": "c" * 64,
        "physical_page": physical_page,
        "pre_ocr_feature_fingerprint_sha256": "d" * 64,
        "provider_identity_sha256": ledger["sha256"],
        "render_runtime_identity_sha256": None,
        "render_specification": None,
        "role_a_used": False,
        "route": "CAUSAL_NATIVE_TEXT",
        "route_plan_sha256": "e" * 64,
        "schema_used": False,
        "selection_receipt_sha256": "f" * 64,
        "sentinel_sha256": "0" * 64,
        "source_sha256": source_sha256,
        "source_size_bytes": len(source_bytes),
    }
    return {
        "request": request,
        "request_sha256": sha256(_canonical_bytes(request)).hexdigest(),
        "source_bytes": source_bytes,
        "document_id": f"sha256:{source_sha256}",
        "physical_page": physical_page,
        "provider_runtime_ledger": ledger,
        "causal_policy_path": project_root / _CAUSAL_POLICY,
        "quality_policy_path": project_root / _QUALITY_POLICY,
        "full_control_identity_sha256": "1" * 64,
    }


def _build(arguments: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_causal_native_text_evidence(**arguments)


def _replay(
    arguments: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> None:
    validate_causal_native_text_evidence_replay(
        **arguments,
        backend=backend,
        result=result,
    )


def _serialized(*values: object) -> str:
    return "\n".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) for value in values
    )


def _all_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        keys.extend(value)
        for item in value.values():
            keys.extend(_all_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_all_keys(item))
    return keys


def test_visible_page_is_deterministic_hash_bound_and_strictly_replayable(
    project_root: Path,
):
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE PAGE"))
    arguments = _arguments(project_root, source)

    backend, result = _build(arguments)
    repeated_backend, repeated_result = _build(arguments)

    assert _canonical_bytes(backend) == _canonical_bytes(repeated_backend)
    assert _canonical_bytes(result) == _canonical_bytes(repeated_result)
    assert backend["format_version"] == BACKEND_FORMAT_VERSION
    assert result["format_version"] == RESULT_FORMAT_VERSION
    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert [word["raw_text"] for word in result["words"]] == ["VISIBLE", "PAGE"]
    assert result["metrics"] == {
        "line_count": 1,
        "word_token_count": 2,
        "quarantined_span_count": 0,
    }
    assert result["backend_payload_sha256"] == sha256(_canonical_bytes(backend)).hexdigest()
    assert result["coordinate_authority"] == {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "coordinate_unit": "MILLI_POINT",
        "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
        "pdf_rotation_applied_to_coordinates": False,
    }
    assert all(value is False for value in result["safety"].values())
    assert not any("rgb" in key.casefold() for key in _all_keys((backend, result)))
    assert "paired_raster" not in _serialized(backend, result).casefold()
    _replay(arguments, backend, result)


def test_white_ghost_and_transparent_text_are_hash_only_and_never_leak(
    project_root: Path,
):
    def draw(page: fitz.Page) -> None:
        page.insert_text((20, 35), "VISIBLE", color=(0, 0, 0))
        page.insert_text((20, 70), "WHITE GHOST SECRET", color=(1, 1, 1))
        page.insert_text(
            (20, 105),
            "TRANSPARENT SECRET",
            color=(0, 0, 0),
            fill_opacity=0,
        )

    arguments = _arguments(project_root, _pdf_bytes(draw))
    backend, result = _build(arguments)

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert [word["raw_text"] for word in result["words"]] == ["VISIBLE"]
    assert {span["text_sha256"] for span in result["quarantined_spans"]} == {
        sha256(b"WHITE GHOST SECRET").hexdigest(),
        sha256(b"TRANSPARENT SECRET").hexdigest(),
    }
    serialized = _serialized(backend, result)
    assert "WHITE GHOST SECRET" not in serialized
    assert "TRANSPARENT SECRET" not in serialized
    for span in result["quarantined_spans"]:
        assert "raw_text" not in span
        assert "normalized_text" not in span
    _replay(arguments, backend, result)


def test_fully_occluded_text_is_quarantined_without_a_semantic_claim(project_root: Path):
    def draw(page: fitz.Page) -> None:
        page.insert_text((20, 35), "VISIBLE", color=(0, 0, 0))
        page.insert_text((100, 100), "OCCLUDED SECRET", color=(0, 0, 0))
        painted_bbox = fitz.Rect(page.get_bboxlog()[-1][1])
        page.draw_rect(painted_bbox, color=(1, 1, 1), fill=(1, 1, 1))

    arguments = _arguments(project_root, _pdf_bytes(draw))
    backend, result = _build(arguments)

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert [word["raw_text"] for word in result["words"]] == ["VISIBLE"]
    assert len(result["quarantined_spans"]) == 1
    assert result["quarantined_spans"][0]["text_sha256"] == sha256(b"OCCLUDED SECRET").hexdigest()
    assert "OCCLUDED SECRET" not in _serialized(backend, result)
    assert all(value is False for value in result["safety"].values())
    _replay(arguments, backend, result)


@pytest.mark.parametrize("rotation", (90, 180, 270))
def test_rotated_pages_keep_unrotated_canonical_millipoints(
    project_root: Path,
    rotation: int,
):
    source = _pdf_bytes(
        lambda page: page.insert_text((100, 100), "ROTATED VISIBLE"),
        rotation=rotation,
    )
    arguments = _arguments(project_root, source)

    backend, result = _build(arguments)

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert result["coordinate_authority"]["canonical_coordinate_system"] == (
        "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT"
    )
    assert result["words"][0]["canonical_bbox_mpt"][0] == 100_000
    _replay(arguments, backend, result)


def test_partial_occlusion_is_terminal_unresolved_without_ocr_or_blank_claim(
    project_root: Path,
):
    def draw(page: fitz.Page) -> None:
        page.insert_text((100, 100), "PARTIAL SECRET", color=(0, 0, 0))
        painted_bbox = fitz.Rect(page.get_bboxlog()[0][1])
        page.draw_rect(
            fitz.Rect(
                painted_bbox.x0,
                painted_bbox.y0,
                painted_bbox.x1 - painted_bbox.width * 0.05,
                painted_bbox.y1,
            ),
            color=(1, 1, 1),
            fill=(1, 1, 1),
        )

    arguments = _arguments(project_root, _pdf_bytes(draw))
    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY"
    assert result["failure_type"] == "CausalNativeTextError"
    assert result["lines"] == []
    assert result["words"] == []
    assert result["quarantined_spans"] == []
    assert result["ocr_fallback_used"] is False
    assert result["source_blank_claimed"] is False
    assert "PARTIAL SECRET" not in _serialized(backend, result)
    _replay(arguments, backend, result)


def test_corrupt_native_text_is_terminal_quality_unresolved_and_not_exposed(
    project_root: Path,
):
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "ÄBROKEN SECRET")),
    )

    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_NATIVE_TEXT_QUALITY"
    assert result["native_text_quality"] == "CORRUPT_TEXT_LAYER"
    assert result["corruption_markers"] == ["Ä"]
    assert result["lines"] == []
    assert result["words"] == []
    assert result["source_blank_claimed"] is False
    assert "ÄBROKEN SECRET" not in _serialized(backend, result)
    _replay(arguments, backend, result)


def test_empty_page_is_terminal_quality_unresolved_without_a_blank_claim(project_root: Path):
    arguments = _arguments(project_root, _pdf_bytes())

    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_NATIVE_TEXT_QUALITY"
    assert result["native_text_quality"] == "NO_TEXT_LAYER"
    assert result["corruption_markers"] == []
    assert result["lines"] == []
    assert result["words"] == []
    assert result["ocr_fallback_used"] is False
    assert result["source_blank_claimed"] is False
    _replay(arguments, backend, result)


def test_corrupt_authenticated_pdf_fails_operationally_without_raw_bytes_in_error(
    project_root: Path,
):
    source = b"%PDF-1.7\nCORRUPT SECRET PATH /bank/file.pdf\n%%EOF\n"
    arguments = _arguments(project_root, source)

    with pytest.raises(CausalNativeTextEvidenceError, match="authenticated PDF") as failure:
        _build(arguments)

    assert "CORRUPT SECRET" not in str(failure.value)
    assert "/bank/file.pdf" not in str(failure.value)


def test_sealed_request_and_provider_foreign_identity_tamper_fail_closed(project_root: Path):
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE"))
    arguments = _arguments(project_root, source)

    unsafe = copy.deepcopy(arguments)
    unsafe["request"]["bank_identity_used"] = True
    unsafe["request_sha256"] = sha256(_canonical_bytes(unsafe["request"])).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="safety boundary"):
        _build(unsafe)

    foreign_runtime = copy.deepcopy(arguments)
    projection = foreign_runtime["provider_runtime_ledger"]
    projection["pymupdf_binding_version"] = "999.0.0"
    ledger_without_identity = {key: value for key, value in projection.items() if key != "sha256"}
    projection["sha256"] = sha256(_canonical_bytes(ledger_without_identity)).hexdigest()
    foreign_runtime["request"]["provider_identity_sha256"] = projection["sha256"]
    foreign_runtime["request_sha256"] = sha256(
        _canonical_bytes(foreign_runtime["request"])
    ).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="runtime identity"):
        _build(foreign_runtime)


def test_policy_bytes_and_symlink_locators_are_authenticated(
    project_root: Path,
    tmp_path: Path,
):
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE"))
    arguments = _arguments(project_root, source)
    mutated = tmp_path / "causal-native-text-v1.yaml"
    mutated.write_bytes((project_root / _CAUSAL_POLICY).read_bytes() + b"\n")
    arguments["causal_policy_path"] = mutated
    with pytest.raises(CausalNativeTextEvidenceError, match="config bytes drifted"):
        _build(arguments)

    symlinked = tmp_path / "quality.yaml"
    symlinked.symlink_to(project_root / _QUALITY_POLICY)
    arguments = _arguments(project_root, source)
    arguments["quality_policy_path"] = symlinked
    with pytest.raises(CausalNativeTextEvidenceError, match="cannot be opened"):
        _build(arguments)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda _backend, result: result.__setitem__("physical_page", True),
        lambda _backend, result: result["words"][0].__setitem__("block_number", 0.0),
        lambda _backend, result: result["words"][0]["canonical_bbox_mpt"].__setitem__(
            0, float("nan")
        ),
        lambda backend, _result: backend.__setitem__("unexpected_semantic_claim", False),
    ),
)
def test_replay_rejects_type_nonfinite_and_extra_field_tamper(
    project_root: Path,
    mutate: Callable[[dict[str, Any], dict[str, Any]], None],
):
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)
    mutate(backend, result)

    with pytest.raises(CausalNativeTextEvidenceError):
        _replay(arguments, backend, result)


def test_replay_rejects_coherent_foreign_and_text_tamper(project_root: Path):
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )

    backend, result = _build(arguments)
    foreign_document_id = f"sha256:{'9' * 64}"
    backend["document_id"] = foreign_document_id
    result["document_id"] = foreign_document_id
    result["backend_payload_sha256"] = sha256(_canonical_bytes(backend)).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="replay drifted"):
        _replay(arguments, backend, result)

    backend, result = _build(arguments)
    backend_word = backend["causal_native_payload"]["words"][0]
    backend_line_word = backend["causal_native_payload"]["lines"][0]["words"][0]
    result_word = result["words"][0]
    result_line_word = result["lines"][0]["words"][0]
    for word in (backend_word, backend_line_word, result_word, result_line_word):
        word["raw_text"] = "FORGED"
    backend["causal_native_payload"]["lines"][0]["raw_text"] = "FORGED"
    result["lines"][0]["raw_text"] = "FORGED"
    result["backend_payload_sha256"] = sha256(_canonical_bytes(backend)).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="replay drifted"):
        _replay(arguments, backend, result)


def test_operational_wrapper_exception_message_is_sanitized(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )

    def fail_with_sensitive_message(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("SECRET SOURCE TEXT /private/bank-file.pdf")

    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v1.read_causal_native_text_page",
        fail_with_sensitive_message,
    )
    with pytest.raises(CausalNativeTextEvidenceError, match="failed operationally") as failure:
        _build(arguments)

    assert "SECRET SOURCE TEXT" not in str(failure.value)
    assert "bank-file.pdf" not in str(failure.value)
