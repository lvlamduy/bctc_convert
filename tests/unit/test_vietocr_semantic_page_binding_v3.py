from __future__ import annotations

import copy
import hashlib
import importlib.util
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts/experiments/vietocr_semantic_page_binding_v3.py"
)
_SPEC = importlib.util.spec_from_file_location("vietocr_semantic_page_binding_v3", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
binding_v3 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = binding_v3
_SPEC.loader.exec_module(binding_v3)


@dataclass
class _ReadyState:
    ready_batch: dict[str, Any]
    audit: dict[str, Any]
    panel: dict[str, Any]
    pages: tuple[dict[str, Any], ...]
    hydration_capabilities: tuple[Any, ...]


@dataclass
class _FreezeState:
    ready_capability: Any
    projection: dict[str, Any]
    manifest: dict[str, Any]
    samples: tuple[dict[str, Any], ...]


@dataclass
class _ReceiptState:
    freeze_capability: Any
    projection: dict[str, Any]
    proposals: tuple[dict[str, Any], ...]


class _FakeReady:
    pass


class _FakeFreeze:
    pass


class _FakeReceipt:
    pass


class _FakeHydration:
    pass


def _box(index: int) -> list[int]:
    return [10, 10 + index * 20, 70, 25 + index * 20]


def _atom_id(index: int) -> str:
    return f"ssv1:atom:{index + 1:064x}"


def _source(mode: str, count: int) -> dict[str, Any]:
    terminal = mode == "terminal"
    route = "CAUSAL_NATIVE_TEXT" if mode == "native" else "DOMINANT_RASTER_OCR"
    lines = []
    atoms = []
    for index in range(0 if terminal else count):
        bbox = _box(index)
        canonical = [item * 1_000 for item in bbox]
        if mode == "native":
            line = {
                "block_number": 0,
                "line_number": index,
                "canonical_bbox_mpt": canonical,
            }
            locator = {
                "kind": "NATIVE_LINE_INDEX",
                "block_number": 0,
                "line_number": index,
            }
            pixel_bbox = None
        else:
            line = {"raw_pixel_bbox": bbox, "canonical_bbox_mpt": canonical}
            locator = {"kind": "OCR_LINE_INDEX", "line_index": index}
            pixel_bbox = bbox
        lines.append(line)
        atoms.append(
            {
                "authority": "AUTHENTICATED_PRIMARY",
                "canonical_bbox_mpt": canonical,
                "kind": "LINE",
                "pixel_bbox": pixel_bbox,
                "source_local_id": _atom_id(index),
                "upstream_locator": locator,
            }
        )
    return {
        "neutral_page_v1": {"atoms": atoms},
        "page_result": {"lines": lines},
        "page_result_format_version": (
            "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
            if mode == "native"
            else "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
            if terminal
            else "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
        ),
        "page_result_ref": {
            "path": "objects/sha256/22/" + "2" * 64 + ".json",
            "sha256": "2" * 64,
            "size_bytes": 456,
        },
        "page_result_sha256": "2" * 64,
        "route": route,
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "source_locator": {
            "source_sha256": "3" * 64,
            "source_size_bytes": 123,
            "physical_page": 42,
            "request_sha256": "4" * 64,
        },
        "terminal": terminal,
        "upstream_status": (
            "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
            if terminal
            else "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
            if mode == "native"
            else "OCR_WORD_BOX_READ_COMPLETE"
        ),
    }


def _install_live_roots(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mode: str,
    count: int = 2,
) -> tuple[dict[str, Any], Any, Any, Any, tuple[Any, ...], _ReadyState]:
    source = _source(mode, count)
    ready = _FakeReady()
    freeze = _FakeFreeze()
    receipt = _FakeReceipt()
    hydration = _FakeHydration()
    hydrations = () if mode == "ordinary" else (hydration,)
    boxes = [_box(index) for index in range(count)]
    render_payload = b"render"
    render_sha256 = hashlib.sha256(render_payload).hexdigest()
    ready_page = {
        "line_bboxes": boxes,
        "line_count": count,
        "page_id": "page-0001",
        "page_ordinal": 1,
        "pixel_height": 100,
        "pixel_width": 100,
        "render_png_bytes": render_payload,
        "render_sha256": render_sha256,
        "render_size_bytes": len(render_payload),
    }
    batch = {"batch_id": "lm8brpv1:batch:" + "6" * 64, "sample_count": count}
    audit_slot = {
        "geometry_authority": (
            "REPLAYED_E0044_READY_V2_CAS"
            if mode == "ordinary"
            else "LIVE_AUTHENTICATED_LINE_PIXEL_HYDRATION_V1"
        ),
        "line_axis_sha256": binding_v3.canonical_json_sha256_v1(boxes),
        "physical_page": 42,
        "render_sha256": render_sha256,
        "render_size_bytes": len(render_payload),
        "source_pdf_sha256": "3" * 64,
    }
    inventory = {
        "authenticated_line_count": 0 if mode == "terminal" else count,
        "render_ref": None,
        "result_format_version": source["page_result_format_version"],
        "result_ref": {
            **copy.deepcopy(source["page_result_ref"]),
            "path": ("output/development/full-v3/objects/sha256/22/" + "2" * 64 + ".json"),
        },
        "route": source["route"],
        "status": source["upstream_status"],
        "unresolved": source["terminal"],
    }
    panel_slot = {
        "freezer_prerequisite": {
            "state": (
                "READY_FOR_OPAQUE_ALL_LINE_FREEZE" if mode == "ordinary" else "BLOCKED_HYDRATION"
            )
        },
        "inventory_evidence": inventory,
        "physical_page": 42,
        "source_pdf_sha256": "3" * 64,
    }
    ready_state = _ReadyState(
        ready_batch=batch,
        audit={"slots": [audit_slot]},
        panel={"slots": [panel_slot]},
        pages=(ready_page,),
        hydration_capabilities=hydrations,
    )
    manifest_samples = []
    frozen_samples = []
    proposals = []
    for index in range(count):
        sample_id = f"page-0001-line-{index:04d}"
        crop_payload = f"crop-{index}".encode()
        crop_sha = hashlib.sha256(crop_payload).hexdigest()
        manifest_samples.append(
            {
                "crop_path": f"output/development/frozen/crops/{sample_id}.png",
                "crop_sha256": crop_sha,
                "crop_size_bytes": 100 + index,
                "line_index": index,
                "page_id": "page-0001",
                "sample_id": sample_id,
            }
        )
        frozen_samples.append(
            {
                "crop_png_bytes": crop_payload,
                "crop_sha256": crop_sha,
                "page_id": "page-0001",
                "sample_id": sample_id,
            }
        )
        proposals.append(
            {
                "crop_sha256": crop_sha,
                "line_index": index,
                "mean_decoded_character_probability": 0.9,
                "normalized_prediction": f"Dòng {index}",
                "page_id": "page-0001",
                "processed_height": 32,
                "processed_width": 96,
                "raw_prediction": f"Dòng {index}",
                "sample_id": sample_id,
            }
        )
    freeze_state = _FreezeState(
        ready_capability=ready,
        projection={"freeze_id": "voalfv3:freeze:" + "8" * 64},
        manifest={"input_batch_id": batch["batch_id"], "samples": manifest_samples},
        samples=tuple(frozen_samples),
    )
    receipt_state = _ReceiptState(
        freeze_capability=freeze,
        projection={
            "freeze_id": freeze_state.projection["freeze_id"],
            "receipt_id": "voalsrv3:receipt:" + "9" * 64,
            "sample_count": count,
        },
        proposals=tuple(proposals),
    )
    hydration_envelope = {
        "adapter_id": (
            "NATIVE_CANONICAL_MPT_TO_DETERMINISTIC_200_DPI_PIXEL_V1"
            if mode == "native"
            else "TERMINAL_PPOCRV6_LINE_GEOMETRY_WORD_QUARANTINE_V1"
        ),
        "lines": [
            {
                "canonical_bbox_mpt": [item * 1_000 for item in box],
                "line_index": index,
                "raw_pixel_bbox": box,
                "source_geometry_sha256": f"{index + 1:x}" * 64,
            }
            for index, box in enumerate(boxes)
        ],
        "source_binding": {"request_sha256": "4" * 64},
    }
    hydration_receipt = {
        "receipt_id": "alpghv1:receipt:" + "a" * 64,
        "source_locator": {
            "physical_page": 42,
            "source_pdf_sha256": "3" * 64,
            "source_size_bytes": 123,
        },
        "upstream_result_ref": {
            "path": ("output/development/finalized-v3/objects/sha256/22/" + "2" * 64 + ".json"),
            "sha256": "2" * 64,
            "size_bytes": 456,
        },
    }

    monkeypatch.setattr(binding_v3, "AuthenticatedLoanMaturity8BankReadyPanelV1", _FakeReady)
    monkeypatch.setattr(binding_v3, "AuthenticatedVietOCRAllLineFreezeV3", _FakeFreeze)
    monkeypatch.setattr(binding_v3, "AuthenticatedVietOCRSemanticReceiptV3", _FakeReceipt)
    monkeypatch.setattr(binding_v3, "AuthenticatedLinePixelHydrationReceiptV1", _FakeHydration)
    monkeypatch.setattr(binding_v3, "validate_source_evidence_projection_v2", lambda value: value)

    def read_ready(_capability: object):
        page = copy.deepcopy(ready_state.pages[0])
        slot = ready_state.audit["slots"][0]
        if slot["render_sha256"] != page["render_sha256"]:
            raise binding_v3._error("fixture live READY audit/render drifted")
        return (
            copy.deepcopy(ready_state.ready_batch),
            copy.deepcopy(ready_state.audit),
            copy.deepcopy(ready_state.panel),
            (page,),
            ready_state.hydration_capabilities,
        )

    monkeypatch.setattr(binding_v3, "_read_ready_live", read_ready)
    monkeypatch.setattr(
        binding_v3,
        "_read_freeze_live",
        lambda capability, parent: (
            copy.deepcopy(freeze_state.projection),
            copy.deepcopy(freeze_state.manifest),
            copy.deepcopy(freeze_state.samples),
        ),
    )
    monkeypatch.setattr(
        binding_v3,
        "_read_receipt_live",
        lambda capability, parent: (
            copy.deepcopy(receipt_state.projection),
            copy.deepcopy(receipt_state.proposals),
        ),
    )
    monkeypatch.setattr(
        binding_v3,
        "_read_hydrations_live",
        lambda capabilities: (
            ()
            if mode == "ordinary"
            else ((copy.deepcopy(hydration_envelope), copy.deepcopy(hydration_receipt), b"render"),)
        ),
    )
    monkeypatch.setattr(binding_v3.freezer_v3, "_png_rgb", lambda payload, label: object())
    monkeypatch.setattr(binding_v3.freezer_v3, "_bbox", lambda value, width, height, label: value)
    monkeypatch.setattr(
        binding_v3.freezer_v3,
        "_crop_bytes",
        lambda image, bbox: (
            f"crop-{boxes.index(bbox)}".encode(),
            96,
            32,
        ),
    )
    return source, ready, freeze, receipt, hydrations, ready_state


@pytest.mark.parametrize(
    ("mode", "expected_mode", "expected_status"),
    [
        (
            "ordinary",
            "ORDINARY_V2_PRIMARY_LINES",
            "BOUND_TO_EXACT_NONTERMINAL_SOURCE_LINE_AXIS",
        ),
        (
            "native",
            "HYDRATED_NATIVE_PRIMARY_LINES",
            "BOUND_TO_EXACT_NONTERMINAL_SOURCE_LINE_AXIS",
        ),
        (
            "terminal",
            "HYDRATED_TERMINAL_LINE_SUPPLEMENT",
            "UNRESOLVED_TERMINAL_SOURCE_NUMERIC_AXIS_UNAVAILABLE",
        ),
    ],
)
def test_generic_modes_replay_and_preserve_terminal_boundary(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    expected_mode: str,
    expected_status: str,
) -> None:
    source, ready, freeze, receipt, hydrations, _state = _install_live_roots(monkeypatch, mode=mode)

    capability = binding_v3.bind_authenticated_vietocr_semantic_page_v3(
        source, ready, freeze, receipt, hydrations
    )
    projection = binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(capability)

    assert (
        source["page_result_ref"]["path"]
        != _state.panel["slots"][0]["inventory_evidence"]["result_ref"]["path"]
    )
    assert projection["binding_mode"] == expected_mode
    assert projection["status"] == expected_status
    assert projection["authority"]["bank_identity_used_for_routing"] is False
    assert projection["authority"]["schema_authority"] is False
    assert projection["metrics"]["all_ready_lines_bound_once"] is True
    assert len(binding_v3.read_authenticated_vietocr_semantic_page_samples_v3(capability)) == 2
    if mode == "terminal":
        assert projection["metrics"]["observation_v2_input_shape_compatible"] is False
        assert projection["metrics"]["source_page_result_line_count"] == 0
        assert projection["metrics"]["terminal_supplement_line_count"] == 2
        assert projection["unresolved_reasons"] == [
            "NUMERIC_SOURCE_LINE_AXIS_UNAVAILABLE",
            "SOURCE_PROJECTION_TERMINAL",
            "TERMINAL_SUPPLEMENT_NOT_AUTHENTICATED_PRIMARY",
        ]
        assert all(
            sample["source_atom"]["source_atom_id"].startswith("vospbv3:terminal-atom:")
            for sample in projection["samples"]
        )
    else:
        assert projection["metrics"]["observation_v2_input_shape_compatible"] is True
        assert projection["unresolved_reasons"] == []
        sample = projection["samples"][0]
        assert set(sample) == binding_v3._SAMPLE_FIELDS
        assert sample["processed_dimensions"] == [96, 32]
        assert set(sample["crop_ref"]) == {"path", "sha256", "size_bytes"}


def test_every_accessor_replays_live_roots_and_fails_closed_on_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, ready, freeze, receipt, hydrations, state = _install_live_roots(
        monkeypatch, mode="ordinary"
    )
    capability = binding_v3.bind_authenticated_vietocr_semantic_page_v3(
        source, ready, freeze, receipt, hydrations
    )

    state.audit["slots"][0]["render_sha256"] = "f" * 64

    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(capability)
    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.read_authenticated_vietocr_semantic_page_samples_v3(capability)


def test_raw_projection_does_not_authenticate_and_capability_is_opaque(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, ready, freeze, receipt, hydrations, _state = _install_live_roots(
        monkeypatch, mode="ordinary"
    )
    capability = binding_v3.bind_authenticated_vietocr_semantic_page_v3(
        source, ready, freeze, receipt, hydrations
    )
    projection = binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(capability)

    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(projection)
    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.AuthenticatedVietOCRSemanticPageBindingV3(object())
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(capability)


def test_projection_validation_rejects_typed_boolean_and_content_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, ready, freeze, receipt, hydrations, _state = _install_live_roots(
        monkeypatch, mode="ordinary"
    )
    capability = binding_v3.bind_authenticated_vietocr_semantic_page_v3(
        source, ready, freeze, receipt, hydrations
    )
    projection = binding_v3.project_authenticated_vietocr_semantic_page_binding_v3(capability)

    forged = copy.deepcopy(projection)
    forged["metrics"]["all_ready_lines_bound_once"] = 1
    material = copy.deepcopy(forged)
    del material["binding_id"]
    forged["binding_id"] = "vospbv3:binding:" + binding_v3.canonical_json_sha256_v1(material)
    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.validate_authenticated_vietocr_semantic_page_binding_v3(forged, capability)


def test_binding_requires_exact_live_capability_types(monkeypatch: pytest.MonkeyPatch) -> None:
    source, ready, freeze, receipt, hydrations, _state = _install_live_roots(
        monkeypatch, mode="ordinary"
    )

    with pytest.raises(binding_v3.VietOCRSemanticPageBindingV3Error):
        binding_v3.bind_authenticated_vietocr_semantic_page_v3(
            source, object(), freeze, receipt, hydrations
        )
