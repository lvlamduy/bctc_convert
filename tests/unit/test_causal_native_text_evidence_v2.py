from __future__ import annotations

import ast
import copy
import json
import socket
from collections.abc import Callable
from hashlib import sha256
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

import fitz
import pytest

from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    BACKEND_FORMAT_VERSION,
    ORDERING_POLICY_RECORD_PATH,
    ORDERING_RECEIPT_FORMAT_VERSION,
    RESULT_FORMAT_VERSION,
    CausalNativeTextEvidenceError,
    build_causal_native_text_evidence_v2,
    validate_causal_native_text_evidence_v2_envelopes,
    validate_causal_native_text_evidence_v2_replay,
)

_CAUSAL_POLICY = Path("config/ocr/causal-native-text-v1.yaml")
_QUALITY_POLICY = Path("config/ocr/native-text-quality-v2.yaml")
_ORDERING_POLICY = Path(ORDERING_POLICY_RECORD_PATH)


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


def _ordering_identity(root: Path) -> dict[str, Any]:
    payload = (root / _ORDERING_POLICY).read_bytes()
    return {
        "path": _ORDERING_POLICY.as_posix(),
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _pdf_bytes(
    draw: Callable[[fitz.Page], None] | None = None,
    *,
    rotation: int = 0,
    cropbox: fitz.Rect | None = None,
) -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    if draw is not None:
        draw(page)
    if cropbox is not None:
        page.set_cropbox(cropbox)
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
        "native_ordering_policy_identity": _ordering_identity(project_root),
        "full_control_identity_sha256": "1" * 64,
    }


def _build(arguments: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_causal_native_text_evidence_v2(**arguments)


def _replay(
    arguments: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> None:
    validate_causal_native_text_evidence_v2_replay(
        **arguments,
        backend=backend,
        result=result,
    )


def _validate_envelopes(
    arguments: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> None:
    request = arguments["request"]
    validate_causal_native_text_evidence_v2_envelopes(
        request=request,
        request_sha256=arguments["request_sha256"],
        document_id=arguments["document_id"],
        source_sha256=request["source_sha256"],
        source_size_bytes=request["source_size_bytes"],
        physical_page=arguments["physical_page"],
        provider_runtime_ledger=arguments["provider_runtime_ledger"],
        native_ordering_policy_identity=arguments["native_ordering_policy_identity"],
        full_control_identity_sha256=arguments["full_control_identity_sha256"],
        backend=backend,
        result=result,
    )


def _word(
    identity: tuple[int, int, int],
    *,
    ordinal: int,
    text: str | None = None,
) -> dict[str, Any]:
    x0 = 10_000 + (ordinal % 10) * 8_000
    y0 = 10_000 + (ordinal // 10) * 12_000
    return {
        "raw_text": text or f"W{ordinal}",
        "score": None,
        "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
        "canonical_bbox_mpt": [x0, y0, x0 + 6_000, y0 + 8_000],
        "block_number": identity[0],
        "line_number": identity[1],
        "word_number": identity[2],
    }


def _line(words: list[dict[str, Any]]) -> dict[str, Any]:
    boxes = [word["canonical_bbox_mpt"] for word in words]
    return {
        "raw_text": " ".join(word["raw_text"] for word in words),
        "score": None,
        "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
        "canonical_bbox_mpt": [
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        ],
        "block_number": words[0]["block_number"],
        "line_number": words[0]["line_number"],
        "words": copy.deepcopy(words),
    }


def _raw_complete(
    identities: list[tuple[int, int, int]],
    *,
    ghost: bool = False,
) -> dict[str, Any]:
    words = [_word(identity, ordinal=index) for index, identity in enumerate(identities)]
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for word in words:
        grouped.setdefault((word["block_number"], word["line_number"]), []).append(word)
    quarantined = []
    if ghost:
        quarantined.append(
            {
                "page": 1,
                "text_sha256": sha256(b"GHOST SECRET").hexdigest(),
                "nonwhitespace_character_count": 11,
                "bbox_mpt": [200_000, 200_000, 220_000, 215_000],
                "block_number": 91,
                "line_number": 7,
                "span_number": 3,
                "color": 0xFFFFFF,
                "alpha": 255,
                "render_sequence": 19,
                "occluding_sequence": None,
                "occluding_object_type": None,
                "reason": "NEAR_WHITE_TEXT_PAINT",
            }
        )
    return {
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "native_text_quality": "USABLE_TEXT_LAYER",
        "corruption_markers": [],
        "lines": [_line(grouped[key]) for key in sorted(grouped)],
        "words": words,
        "quarantined_spans": quarantined,
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }


def _raw_visibility(failure_type: Any) -> dict[str, Any]:
    return {
        "status": "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "failure_type": failure_type,
        "lines": [],
        "words": [],
        "quarantined_spans": [],
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }


def _patch_raw(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        lambda *_args, **_kwargs: copy.deepcopy(payload),
    )


def _serialized(*values: object) -> str:
    return "\n".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) for value in values
    )


def test_visible_page_is_deterministic_directly_bound_and_replayable(
    project_root: Path,
) -> None:
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE PAGE"))
    arguments = _arguments(project_root, source)

    backend, result = _build(arguments)
    repeated_backend, repeated_result = _build(arguments)

    assert _canonical_bytes(backend) == _canonical_bytes(repeated_backend)
    assert _canonical_bytes(result) == _canonical_bytes(repeated_result)
    assert backend["format_version"] == BACKEND_FORMAT_VERSION
    assert result["format_version"] == RESULT_FORMAT_VERSION
    assert result["ordering_receipt"]["format_version"] == ORDERING_RECEIPT_FORMAT_VERSION
    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert [word["raw_text"] for word in result["words"]] == ["VISIBLE", "PAGE"]
    assert backend["provider_runtime_ledger"]["provider"] == (
        "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1"
    )
    assert len(backend["provider_runtime_ledger"]["config_records"]) == 2
    assert backend["ordering_policy_identity"] == arguments["native_ordering_policy_identity"]
    assert result["ordering_policy_identity"] == arguments["native_ordering_policy_identity"]
    assert (
        result["ordering_receipt"]["ordering_policy_identity"]
        == arguments["native_ordering_policy_identity"]
    )
    assert result["metrics"] == {
        "line_count": 1,
        "word_token_count": 2,
        "ghost_quarantined_span_count": 0,
        "ordering_quarantined_raw_line_run_count": 0,
        "ordering_quarantined_raw_word_count": 0,
        "noncontiguous_line_identity_count": 0,
    }
    assert "raw_causal_native_wrapper_payload" in backend
    assert "raw_causal_native_wrapper_payload" not in result
    assert all(value is False for value in result["safety"].values())
    _validate_envelopes(arguments, backend, result)
    _replay(arguments, backend, result)


def test_synthetic_visual_order_16_before_2_is_accepted_without_lexical_reordering(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_complete([(16, 0, 0), (2, 0, 0), (2, 0, 1)])
    _patch_raw(monkeypatch, raw)
    arguments = _arguments(project_root, _pdf_bytes())

    backend, result = _build(arguments)

    assert [(line["block_number"], line["line_number"]) for line in result["lines"]] == [
        (16, 0),
        (2, 0),
    ]
    assert result["words"] == [word for line in result["lines"] for word in line["words"]]
    assert backend["raw_causal_native_wrapper_payload"]["lines"][0]["block_number"] == 2
    assert result["ordering_receipt"]["status"] == "CONTIGUOUS_SOURCE_ORDER_ACCEPTED"
    _replay(arguments, backend, result)


_VPB_P2_IDENTITIES = [
    *((0, 0, index) for index in range(10)),
    (1, 0, 0),
    (1, 0, 1),
    (16, 0, 0),
    (2, 0, 0),
    (2, 0, 1),
    (2, 0, 2),
    (17, 0, 0),
    (2, 1, 0),
    (11, 0, 0),
    *((3, 0, index) for index in range(11)),
    (7, 0, 0),
    (3, 1, 0),
    (12, 0, 0),
    *((4, 0, index) for index in range(11)),
    (8, 0, 0),
    (4, 1, 0),
    (13, 0, 0),
    *((5, 0, index) for index in range(11)),
    (9, 0, 0),
    (5, 1, 0),
    (14, 0, 0),
    *((6, 0, index) for index in range(11)),
    (10, 0, 0),
    (6, 1, 0),
    (15, 0, 0),
]


def test_exact_vpb_p2_word_identity_pattern_preserves_all_75_words_and_23_runs(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert len(_VPB_P2_IDENTITIES) == 75
    assert len({identity[:2] for identity in _VPB_P2_IDENTITIES}) == 23
    assert _VPB_P2_IDENTITIES[12] == (16, 0, 0)
    raw = _raw_complete(_VPB_P2_IDENTITIES)
    assert [raw["lines"][index]["block_number"] for index in range(3)] == [0, 1, 2]
    _patch_raw(monkeypatch, raw)

    backend, result = _build(_arguments(project_root, _pdf_bytes()))

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert result["metrics"]["word_token_count"] == 75
    assert result["metrics"]["line_count"] == 23
    assert result["lines"][2]["block_number"] == 16
    assert result["lines"][3]["block_number"] == 2
    assert result["words"] == [word for line in result["lines"] for word in line["words"]]
    assert backend["raw_causal_native_wrapper_payload"]["words"] == result["words"]


def test_authenticated_real_vpb_p2_request_fba554_repairs_forensic_order(
    project_root: Path,
) -> None:
    plan_path = (
        project_root / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
        "wave-1-role-b-page-read-plan.json"
    )
    if not plan_path.is_file():
        pytest.skip("sealed Wave-1 plan must be explicitly restored for the VPB-p2 gate")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    request_sha256 = "fba5545127196a9f82c432c9045bbaacfa5bfa5f1cd6d10880756b569955e479"
    matches = [
        page
        for document in plan["documents"]
        for page in document["pages"]
        if page["request_sha256"] == request_sha256
    ]
    assert len(matches) == 1
    page_record = matches[0]
    request = page_record["request"]
    assert request["source_sha256"] == (
        "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
    )
    assert request["physical_page"] == 2
    source_candidates = []
    source_root = project_root / "vietstock_bctc"
    if source_root.is_dir():
        for candidate in source_root.rglob("*.pdf"):
            if candidate.stat().st_size != request["source_size_bytes"]:
                continue
            payload = candidate.read_bytes()
            if sha256(payload).hexdigest() == request["source_sha256"]:
                source_candidates.append(payload)
    if not source_candidates:
        pytest.skip("source SHA 614be887... must be explicitly hydrated for the real VPB-p2 gate")
    assert len(source_candidates) == 1
    source_bytes = source_candidates[0]
    arguments = {
        "request": request,
        "request_sha256": request_sha256,
        "source_bytes": source_bytes,
        "document_id": f"sha256:{request['source_sha256']}",
        "physical_page": 2,
        "provider_runtime_ledger": plan["causal_native_runtime_ledger"],
        "causal_policy_path": project_root / _CAUSAL_POLICY,
        "quality_policy_path": project_root / _QUALITY_POLICY,
        "native_ordering_policy_identity": _ordering_identity(project_root),
        "full_control_identity_sha256": plan["execution_plan_sha256"],
    }

    backend, result = _build(arguments)
    raw = backend["raw_causal_native_wrapper_payload"]
    raw_flattened = [word for line in raw["lines"] for word in line["words"]]

    assert sha256(_canonical_bytes(raw)).hexdigest() == (
        "bb5fa4bd80d58c62342584c172b875f905c2c40dedbd9dbe42720da8818dbd0a"
    )
    assert len(_canonical_bytes(raw)) == 31_722
    assert sha256(_canonical_bytes(raw["lines"])).hexdigest() == (
        "6df23295446a37b659d545b714b92887c2652dd7475776e151a9395e922d46dd"
    )
    assert len(_canonical_bytes(raw["lines"])) == 17_918
    assert sha256(_canonical_bytes(raw["words"])).hexdigest() == (
        "7762ccabaca1204b2a2fbdde82b49276458386f030624c07fa4b110734c324da"
    )
    assert len(_canonical_bytes(raw["words"])) == 13_598
    assert sha256(_canonical_bytes(raw_flattened)).hexdigest() == (
        "9e20d536d8423a8ceac7b1da9924cddccd7a06dff63dc68471eb3d0cf8fa574f"
    )
    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert result["metrics"]["word_token_count"] == 75
    assert result["metrics"]["line_count"] == 23
    assert tuple(
        result["words"][12][key] for key in ("block_number", "line_number", "word_number")
    ) == (16, 0, 0)
    assert [(line["block_number"], line["line_number"]) for line in result["lines"]][2:4] == [
        (16, 0),
        (2, 0),
    ]
    assert result["words"] == [word for line in result["lines"] for word in line["words"]]
    assert sha256(_canonical_bytes(result["words"])).hexdigest() == (
        "7762ccabaca1204b2a2fbdde82b49276458386f030624c07fa4b110734c324da"
    )
    _replay(arguments, backend, result)


def test_a_b_a_is_terminal_hash_count_only_while_ghost_provenance_stays_separate(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_complete([(1, 0, 0), (2, 0, 0), (1, 0, 1)], ghost=True)
    raw["words"][0]["raw_text"] = "ORDERING SECRET A"
    raw["words"][1]["raw_text"] = "ORDERING SECRET B"
    raw["words"][2]["raw_text"] = "ORDERING SECRET A2"
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for word in raw["words"]:
        grouped.setdefault((word["block_number"], word["line_number"]), []).append(word)
    raw["lines"] = [_line(grouped[key]) for key in sorted(grouped)]
    _patch_raw(monkeypatch, raw)
    arguments = _arguments(project_root, _pdf_bytes())

    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY"
    assert result["failure_type"] == "NoncontiguousNativeLineIdentity"
    assert result["lines"] == []
    assert result["words"] == []
    assert result["ordering_receipt"]["status"] == ("NONCONTIGUOUS_LINE_ORDER_QUARANTINED")
    assert set(result["ordering_receipt"]) == {
        "format_version",
        "policy",
        "ordering_policy_identity",
        "source_word_order",
        "line_projection",
        "status",
        "source_word_count",
        "line_run_count",
        "distinct_line_identity_count",
        "noncontiguous_line_identity_count",
        "source_words_sha256",
        "line_runs_sha256",
        "noncontiguous_line_identities_sha256",
    }
    assert result["metrics"] == {
        "line_count": 0,
        "word_token_count": 0,
        "ghost_quarantined_span_count": 1,
        "ordering_quarantined_raw_line_run_count": 3,
        "ordering_quarantined_raw_word_count": 3,
        "noncontiguous_line_identity_count": 1,
    }
    assert len(result["quarantined_spans"]) == 1
    assert result["quarantined_spans"][0]["text_sha256"] == sha256(b"GHOST SECRET").hexdigest()
    assert "GHOST SECRET" not in _serialized(backend, result)
    assert "ORDERING SECRET" not in _serialized(result)
    assert "ORDERING SECRET" in _serialized(backend)
    _replay(arguments, backend, result)


def test_a_word_2_b_a_word_0_is_contiguity_terminal_not_cross_run_order_abort(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_complete([(1, 0, 2), (2, 0, 0), (1, 0, 0)])
    _patch_raw(monkeypatch, raw)
    arguments = _arguments(project_root, _pdf_bytes())

    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY"
    assert result["failure_type"] == "NoncontiguousNativeLineIdentity"
    assert result["lines"] == []
    assert result["words"] == []
    assert result["ordering_receipt"]["line_run_count"] == 3
    assert result["ordering_receipt"]["noncontiguous_line_identity_count"] == 1
    _replay(arguments, backend, result)


@pytest.mark.parametrize(
    ("identities", "message"),
    (
        ([(1, 0, 0), (1, 0, 0)], "duplicated"),
        ([(1, 0, 1), (1, 0, 0)], "order drifted"),
    ),
)
def test_duplicate_and_within_line_order_drift_abort_operationally(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    identities: list[tuple[int, int, int]],
    message: str,
) -> None:
    raw = _raw_complete(identities)
    _patch_raw(monkeypatch, raw)

    with pytest.raises(CausalNativeTextEvidenceError, match=message):
        _build(_arguments(project_root, _pdf_bytes()))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda raw: raw["words"][0].__setitem__("block_number", True),
        lambda raw: raw["words"][0]["canonical_bbox_mpt"].__setitem__(0, float("nan")),
        lambda raw: raw["words"][0]["canonical_bbox_mpt"].__setitem__(0, -1),
        lambda raw: raw["words"][0].__setitem__("unexpected", False),
    ),
)
def test_malformed_nonfinite_typed_and_out_of_cropbox_raw_words_abort(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    raw = _raw_complete([(1, 0, 0)])
    mutate(raw)
    _patch_raw(monkeypatch, raw)

    with pytest.raises(CausalNativeTextEvidenceError):
        _build(_arguments(project_root, _pdf_bytes()))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda raw: raw["words"][0]["canonical_bbox_mpt"].__setitem__(
            2, raw["words"][0]["canonical_bbox_mpt"][0]
        ),
        lambda raw: raw["lines"][0]["canonical_bbox_mpt"].__setitem__(
            3, raw["lines"][0]["canonical_bbox_mpt"][1]
        ),
        lambda raw: raw["quarantined_spans"][0]["bbox_mpt"].__setitem__(
            2, raw["quarantined_spans"][0]["bbox_mpt"][0]
        ),
    ),
)
def test_zero_area_raw_word_line_and_ghost_geometry_abort(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    raw = _raw_complete([(1, 0, 0)], ghost=True)
    mutate(raw)
    _patch_raw(monkeypatch, raw)

    with pytest.raises(CausalNativeTextEvidenceError):
        _build(_arguments(project_root, _pdf_bytes()))


def test_post_millipoint_rounding_cropbox_collapse_aborts() -> None:
    module = __import__(
        "bctc_ai.ocr.causal_native_text_evidence_v2", fromlist=["_coordinate_authority"]
    )

    class PageWithSubMillipointWidth:
        cropbox = fitz.Rect(0, 0, 0.0004, 10)
        mediabox = fitz.Rect(0, 0, 1, 10)
        rotation = 0

    with pytest.raises(CausalNativeTextEvidenceError, match="positive area"):
        module._coordinate_authority(PageWithSubMillipointWidth())


@pytest.mark.parametrize("rotation", (0, 90, 180, 270))
def test_rotations_and_nonzero_cropbox_offsets_are_explicit_and_bounded(
    project_root: Path,
    rotation: int,
) -> None:
    source = _pdf_bytes(
        lambda page: page.insert_text((100, 100), "CROPPED VISIBLE"),
        rotation=rotation,
        cropbox=fitz.Rect(50, 40, 350, 240),
    )

    backend, result = _build(_arguments(project_root, source))

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert result["coordinate_authority"] == {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "coordinate_unit": "MILLI_POINT",
        "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
        "pdf_rotation_applied_to_coordinates": False,
        "pdf_rotation_degrees": rotation,
        "canonical_cropbox_bounds_mpt": [0, 0, 300_000, 200_000],
        "source_cropbox_mpt": [50_000, 40_000, 350_000, 240_000],
        "source_mediabox_mpt": [0, 0, 400_000, 300_000],
    }
    assert result["words"][0]["canonical_bbox_mpt"][0] == 50_000
    bounds = result["coordinate_authority"]["canonical_cropbox_bounds_mpt"]
    assert all(
        0 <= box[0] <= box[2] <= bounds[2] and 0 <= box[1] <= box[3] <= bounds[3]
        for box in (word["canonical_bbox_mpt"] for word in result["words"])
    )
    assert backend["coordinate_authority"] == result["coordinate_authority"]


def test_white_ghost_is_hash_only_and_never_leaks(project_root: Path) -> None:
    def draw(page: fitz.Page) -> None:
        page.insert_text((20, 35), "VISIBLE", color=(0, 0, 0))
        page.insert_text((20, 70), "WHITE GHOST SECRET", color=(1, 1, 1))

    arguments = _arguments(project_root, _pdf_bytes(draw))
    backend, result = _build(arguments)

    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert [word["raw_text"] for word in result["words"]] == ["VISIBLE"]
    assert result["metrics"]["ghost_quarantined_span_count"] == 1
    assert (
        result["quarantined_spans"][0]["text_sha256"] == sha256(b"WHITE GHOST SECRET").hexdigest()
    )
    assert "WHITE GHOST SECRET" not in _serialized(backend, result)
    _replay(arguments, backend, result)


def test_partial_visibility_terminal_remains_textless_without_fallback_or_blank_claim(
    project_root: Path,
) -> None:
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
    assert result["lines"] == []
    assert result["words"] == []
    assert result["ordering_receipt"]["status"] == (
        "SOURCE_ORDER_NOT_APPLICABLE_TO_UPSTREAM_TERMINAL"
    )
    assert result["ocr_fallback_used"] is False
    assert result["source_blank_claimed"] is False
    assert "PARTIAL SECRET" not in _serialized(backend, result)
    _replay(arguments, backend, result)


@pytest.mark.parametrize(
    "unsafe_failure_type",
    ("Érror", "A" * 129, "Bad-Type", "7Bad", True, 7, None),
)
def test_raw_visibility_failure_type_is_exact_ascii_bounded_v1_vocabulary(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_failure_type: Any,
) -> None:
    _patch_raw(monkeypatch, _raw_visibility(unsafe_failure_type))

    with pytest.raises(CausalNativeTextEvidenceError, match="failure type"):
        _build(_arguments(project_root, _pdf_bytes()))


@pytest.mark.parametrize("unsafe_failure_type", ("Érror", "A" * 129, "Bad-Type", "7Bad", True))
def test_replay_rejects_unsafe_public_visibility_failure_type(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_failure_type: Any,
) -> None:
    _patch_raw(monkeypatch, _raw_visibility("CausalNativeTextError"))
    arguments = _arguments(project_root, _pdf_bytes())
    backend, result = _build(arguments)
    result["failure_type"] = unsafe_failure_type

    with pytest.raises(CausalNativeTextEvidenceError, match="failure type"):
        _replay(arguments, backend, result)


@pytest.mark.parametrize(
    ("draw", "quality", "secret"),
    (
        (None, "NO_TEXT_LAYER", None),
        (
            lambda page: page.insert_text((20, 40), "ÄBROKEN SECRET"),
            "CORRUPT_TEXT_LAYER",
            "ÄBROKEN SECRET",
        ),
    ),
)
def test_empty_and_corrupt_quality_terminals_remain_unresolved(
    project_root: Path,
    draw: Callable[[fitz.Page], None] | None,
    quality: str,
    secret: str | None,
) -> None:
    arguments = _arguments(project_root, _pdf_bytes(draw))
    backend, result = _build(arguments)

    assert result["status"] == "UNRESOLVED_NATIVE_TEXT_QUALITY"
    assert result["native_text_quality"] == quality
    assert result["lines"] == []
    assert result["words"] == []
    assert result["source_blank_claimed"] is False
    if secret is not None:
        assert secret not in _serialized(backend, result)
    _replay(arguments, backend, result)


def test_role_a_request_foreign_source_and_runtime_identity_fail_closed(
    project_root: Path,
) -> None:
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE"))

    role_a = _arguments(project_root, source)
    role_a["request"]["role_a_used"] = True
    role_a["request_sha256"] = sha256(_canonical_bytes(role_a["request"])).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="safety boundary"):
        _build(role_a)

    foreign_source = _arguments(project_root, source)
    foreign_source["source_bytes"] = source + b"FOREIGN"
    with pytest.raises(CausalNativeTextEvidenceError, match="source size"):
        _build(foreign_source)

    foreign_runtime = _arguments(project_root, source)
    ledger = foreign_runtime["provider_runtime_ledger"]
    ledger["pymupdf_binding_version"] = "999.0.0"
    projection = {key: value for key, value in ledger.items() if key != "sha256"}
    ledger["sha256"] = sha256(_canonical_bytes(projection)).hexdigest()
    foreign_runtime["request"]["provider_identity_sha256"] = ledger["sha256"]
    foreign_runtime["request_sha256"] = sha256(
        _canonical_bytes(foreign_runtime["request"])
    ).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="runtime identity"):
        _build(foreign_runtime)


def test_ordering_policy_control_identity_and_live_bytes_are_directly_authenticated(
    project_root: Path,
) -> None:
    arguments = _arguments(project_root, _pdf_bytes())

    wrong_path = copy.deepcopy(arguments)
    wrong_path["native_ordering_policy_identity"]["path"] = "foreign.yaml"
    with pytest.raises(CausalNativeTextEvidenceError, match="path drifted"):
        _build(wrong_path)

    wrong_hash = copy.deepcopy(arguments)
    wrong_hash["native_ordering_policy_identity"]["sha256"] = "9" * 64
    with pytest.raises(CausalNativeTextEvidenceError, match="bytes drifted"):
        _build(wrong_hash)

    wrong_type = copy.deepcopy(arguments)
    wrong_type["native_ordering_policy_identity"]["size_bytes"] = float(
        wrong_type["native_ordering_policy_identity"]["size_bytes"]
    )
    with pytest.raises(CausalNativeTextEvidenceError, match="positive integer"):
        _build(wrong_type)


def test_ordering_policy_change_during_read_is_detected(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_root = tmp_path / "config" / "ocr"
    config_root.mkdir(parents=True)
    for relative in (_CAUSAL_POLICY, _QUALITY_POLICY, _ORDERING_POLICY):
        (config_root / relative.name).write_bytes((project_root / relative).read_bytes())
    source = _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE"))
    arguments = _arguments(project_root, source)
    arguments["causal_policy_path"] = config_root / _CAUSAL_POLICY.name
    arguments["quality_policy_path"] = config_root / _QUALITY_POLICY.name
    original = __import__(
        "bctc_ai.ocr.causal_native_text_evidence_v2", fromlist=["read_causal_native_text_page"]
    ).read_causal_native_text_page

    def mutate_policy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        payload = original(*args, **kwargs)
        (config_root / _ORDERING_POLICY.name).write_bytes(
            (config_root / _ORDERING_POLICY.name).read_bytes() + b"\n"
        )
        return payload

    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        mutate_policy,
    )
    with pytest.raises(CausalNativeTextEvidenceError, match="changed during"):
        _build(arguments)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda _backend, result: result.__setitem__("physical_page", True),
        lambda _backend, result: result["coordinate_authority"].__setitem__(
            "pdf_rotation_degrees", 0.0
        ),
        lambda _backend, result: result["coordinate_authority"][
            "canonical_cropbox_bounds_mpt"
        ].__setitem__(0, -0.0),
        lambda _backend, result: result["ordering_receipt"].__setitem__(
            "source_word_count", float("nan")
        ),
        lambda backend, _result: backend.__setitem__("unexpected_semantic_claim", False),
    ),
)
def test_replay_rejects_typed_signed_zero_nonfinite_and_extra_field_tamper(
    project_root: Path,
    mutate: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)
    mutate(backend, result)

    with pytest.raises(CausalNativeTextEvidenceError):
        _replay(arguments, backend, result)


def test_replay_rejects_zero_area_public_word_geometry(project_root: Path) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)
    result["words"][0]["canonical_bbox_mpt"][2] = result["words"][0]["canonical_bbox_mpt"][0]

    with pytest.raises(CausalNativeTextEvidenceError, match="positive-area"):
        _replay(arguments, backend, result)


def test_public_structural_validator_never_invokes_provider_or_reads_source(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)

    def forbidden(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("provider must not be invoked by structural validation")

    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        forbidden,
    )
    _validate_envelopes(arguments, backend, result)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda backend, result: (
            backend.__setitem__("status", "ARBITRARY_TERMINAL"),
            result.__setitem__("status", "ARBITRARY_TERMINAL"),
        ),
        lambda backend, result: (
            backend.__setitem__("full_control_identity_sha256", "9" * 64),
            result.__setitem__("full_control_identity_sha256", "9" * 64),
        ),
        lambda backend, result: (
            backend.__setitem__("provider_identity_sha256", "9" * 64),
            result.__setitem__("provider_identity_sha256", "9" * 64),
        ),
        lambda backend, result: (
            backend.__setitem__("request", {**backend["request"], "role_a_used": True}),
            result.__setitem__("request", {**result["request"], "role_a_used": True}),
        ),
        lambda backend, result: (
            backend.__setitem__("source_size_bytes", True),
            result.__setitem__("source_size_bytes", True),
        ),
        lambda backend, result: (
            backend.__setitem__("physical_page", 1.0),
            result.__setitem__("physical_page", 1.0),
        ),
    ),
)
def test_public_structural_validator_rejects_arbitrary_status_and_foreign_boundaries(
    project_root: Path,
    mutate: Callable[[dict[str, Any], dict[str, Any]], object],
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)
    mutate(backend, result)
    result["backend_payload_sha256"] = sha256(_canonical_bytes(backend)).hexdigest()

    with pytest.raises(CausalNativeTextEvidenceError):
        _validate_envelopes(arguments, backend, result)


def test_public_structural_validator_rejects_unsafe_expected_request_and_ledger(
    project_root: Path,
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )
    backend, result = _build(arguments)

    unsafe_request = copy.deepcopy(arguments)
    unsafe_request["request"]["role_a_used"] = True
    unsafe_request["request_sha256"] = sha256(
        _canonical_bytes(unsafe_request["request"])
    ).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="request safety"):
        _validate_envelopes(unsafe_request, backend, result)

    unsafe_ledger = copy.deepcopy(arguments)
    unsafe_ledger["provider_runtime_ledger"]["ocr_fallback_allowed"] = True
    ledger_projection = {
        key: value
        for key, value in unsafe_ledger["provider_runtime_ledger"].items()
        if key != "sha256"
    }
    unsafe_ledger["provider_runtime_ledger"]["sha256"] = sha256(
        _canonical_bytes(ledger_projection)
    ).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="provider ledger boundary"):
        _validate_envelopes(unsafe_ledger, backend, result)


def test_replay_rejects_coherent_text_receipt_and_foreign_control_tamper(
    project_root: Path,
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )

    backend, result = _build(arguments)
    backend_word = backend["raw_causal_native_wrapper_payload"]["words"][0]
    backend_line_word = backend["raw_causal_native_wrapper_payload"]["lines"][0]["words"][0]
    result_word = result["words"][0]
    result_line_word = result["lines"][0]["words"][0]
    for word in (backend_word, backend_line_word, result_word, result_line_word):
        word["raw_text"] = "FORGED"
    backend["raw_causal_native_wrapper_payload"]["lines"][0]["raw_text"] = "FORGED"
    result["lines"][0]["raw_text"] = "FORGED"
    result["backend_payload_sha256"] = sha256(_canonical_bytes(backend)).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError):
        _replay(arguments, backend, result)

    backend, result = _build(arguments)
    backend["full_control_identity_sha256"] = "9" * 64
    result["full_control_identity_sha256"] = "9" * 64
    result["backend_payload_sha256"] = sha256(_canonical_bytes(backend)).hexdigest()
    with pytest.raises(CausalNativeTextEvidenceError, match="full_control_identity"):
        _replay(arguments, backend, result)


def test_operational_wrapper_exception_is_sanitized(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )

    def fail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("SECRET SOURCE TEXT /private/bank-file.pdf")

    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        fail,
    )
    with pytest.raises(CausalNativeTextEvidenceError, match="failed operationally") as failure:
        _build(arguments)
    assert "SECRET SOURCE TEXT" not in str(failure.value)
    assert "bank-file.pdf" not in str(failure.value)


@pytest.mark.parametrize("connection_api", ("create_connection", "connect", "connect_ex"))
def test_provider_network_attempt_aborts_sanitized_and_restores_hooks(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    connection_api: str,
) -> None:
    module = __import__(
        "bctc_ai.ocr.causal_native_text_evidence_v2", fromlist=["read_causal_native_text_page"]
    )
    original_provider = module.read_causal_native_text_page
    original_create_connection = socket.create_connection
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    arguments = _arguments(
        project_root,
        _pdf_bytes(lambda page: page.insert_text((20, 40), "VISIBLE")),
    )

    def attempt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        target = ("SECRET-NETWORK-TARGET.invalid", 443)
        if connection_api == "create_connection":
            socket.create_connection(target, timeout=0.01)
        else:
            with socket.socket() as client:
                getattr(client, connection_api)(target)
        raise AssertionError("network denial did not abort the provider")

    monkeypatch.setattr(module, "read_causal_native_text_page", attempt)
    with pytest.raises(CausalNativeTextEvidenceError, match="failed operationally") as failure:
        _build(arguments)
    assert "SECRET-NETWORK-TARGET" not in str(failure.value)
    assert socket.create_connection is original_create_connection
    assert socket.socket.connect is original_connect
    assert socket.socket.connect_ex is original_connect_ex

    monkeypatch.setattr(module, "read_causal_native_text_page", original_provider)
    backend, result = _build(arguments)
    assert result["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    _replay(arguments, backend, result)


def test_caught_provider_network_attempt_still_aborts_without_evidence(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_complete([(1, 0, 0)])

    def catch_denial(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        try:
            socket.create_connection(("SECRET-CAUGHT-TARGET.invalid", 443), timeout=0.01)
        except RuntimeError:
            pass
        return copy.deepcopy(raw)

    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        catch_denial,
    )
    with pytest.raises(CausalNativeTextEvidenceError, match="failed operationally") as failure:
        _build(_arguments(project_root, _pdf_bytes()))
    assert "SECRET-CAUGHT-TARGET" not in str(failure.value)


def test_nested_network_guard_exception_restores_each_prior_hook_exactly() -> None:
    module = __import__(
        "bctc_ai.ocr.causal_native_text_evidence_v2", fromlist=["_deny_network_connections"]
    )
    original_hooks = (
        socket.create_connection,
        socket.socket.connect,
        socket.socket.connect_ex,
    )

    with module._deny_network_connections():
        outer_hooks = (
            socket.create_connection,
            socket.socket.connect,
            socket.socket.connect_ex,
        )
        assert outer_hooks != original_hooks
        with pytest.raises(ValueError, match="nested failure"):
            with module._deny_network_connections():
                inner_hooks = (
                    socket.create_connection,
                    socket.socket.connect,
                    socket.socket.connect_ex,
                )
                assert inner_hooks != outer_hooks
                raise ValueError("nested failure")
        assert (
            socket.create_connection,
            socket.socket.connect,
            socket.socket.connect_ex,
        ) == outer_hooks
    assert (
        socket.create_connection,
        socket.socket.connect,
        socket.socket.connect_ex,
    ) == original_hooks


def test_v1_import_is_exact_generic_helper_closure_without_public_adapter_calls(
    project_root: Path,
) -> None:
    module_path = project_root / "src/bctc_ai/ocr/causal_native_text_evidence_v2.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "bctc_ai.ocr.causal_native_text_evidence_v1"
    ]

    assert len(imports) == 1
    assert {alias.name for alias in imports[0].names} == {
        "CausalNativeTextEvidenceError",
        "_authenticated_policy_copies",
        "_canonical_clone",
        "_canonical_json_bytes",
        "_canonical_json_sha256",
        "_require_nonnegative_integer",
        "_require_positive_integer",
        "_require_sha256",
        "_same_typed_json",
        "_stable_regular_bytes",
        "_validate_json_tree",
        "_validate_provider_runtime_ledger",
        "_validate_request",
    }
    imported_names = {alias.name for alias in imports[0].names}
    assert "build_causal_native_text_evidence" not in imported_names
    assert "validate_causal_native_text_evidence_replay" not in imported_names
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            alias.name.partition(".")[0] in {"requests", "urllib", "httpx", "boto3"}
            for alias in node.names
        )
        for node in ast.walk(tree)
    )
