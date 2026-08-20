from __future__ import annotations

import copy
import hashlib
import io
import json
import pickle
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_semantic_index_v1 as index
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _png(width: int = 103, height: int = 20) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


def _fixture() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
    bytes,
]:
    plan = {
        "plan_id": "ffslpv1:plan:" + "1" * 64,
        "documents": [
            {
                "document_ordinal": 1,
                "page_count": 2,
                "private_provenance": {
                    "bank": "ACB",
                    "period": "Q1",
                    "scope": "CONSOLIDATED",
                    "year": 2026,
                },
                "source_pdf_ref": {
                    "path": "vietstock_bctc/ACB/source.pdf",
                    "sha256": "a" * 64,
                    "size_bytes": 10,
                },
            }
        ],
    }
    crop_payloads = [_png(), _png(80, 20)]
    samples = []
    private_samples = []
    proposals = []
    crops = []
    for offset, payload in enumerate(crop_payloads):
        sample_id = f"sample-{offset + 1:09d}"
        digest = hashlib.sha256(payload).hexdigest()
        reference = {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                f"document-0001/page-{offset + 1:04d}/crops/line-0000.png"
            ),
            "sha256": digest,
            "size_bytes": len(payload),
        }
        samples.append({"crop_ref": reference, "sample_id": sample_id})
        private_samples.append(
            {
                "document_ordinal": 1,
                "line_ordinal": 0,
                "physical_page": offset + 1,
                "sample_id": sample_id,
                "source_bbox_raw_pixels": [10, 20, 110, 40],
            }
        )
        width, height = index._processed_dimensions(payload)
        proposals.append(
            {
                "crop_sha256": digest,
                "format_version": index.runner_v1.PROPOSAL_FORMAT_VERSION,
                "mean_decoded_character_probability": None if offset else 0.9,
                "processed_height": height,
                "processed_width": width,
                "raw_prediction": "Nợ trùng hạn" if offset == 0 else "",
                "sample_id": sample_id,
            }
        )
        crops.append({"crop_png_bytes": payload, "crop_sha256": digest, "sample_id": sample_id})
    batch = {
        "batch_id": "ffslcv1:batch:" + "2" * 64,
        "sample_count": len(samples),
        "samples": samples,
    }
    private_index = {"samples": private_samples}
    proposal_payload = b"".join(canonical_json_bytes_v1(item) for item in proposals)
    return plan, batch, private_index, crops, proposal_payload


def test_build_index_preserves_raw_empty_and_accentless_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, batch, private_index, crops, proposal_payload = _fixture()
    chunks = [tuple(crops), ()]
    monkeypatch.setattr(
        index.archive_v1,
        "open_authenticated_family_first_semantic_label_reader_session_v1",
        lambda _cap: object(),
    )
    monkeypatch.setattr(
        index.archive_v1,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda _session, **_kwargs: chunks.pop(0),
    )
    stage = tmp_path / "stage"
    stage.mkdir()
    manifest = index._build_index_stage(
        tmp_path,
        stage,
        object(),
        {"archive_id": "ffslav1:archive:" + "3" * 64},
        batch,
        plan,
        private_index,
        {"run_id": "ffvocrv1:run:" + "4" * 64},
        proposal_payload,
    )
    assert manifest["metrics"]["sample_count"] == 2
    assert manifest["metrics"]["empty_prediction_count"] == 1
    assert manifest["metrics"]["null_probability_count"] == 1
    document = json.loads((stage / "documents/document-0001.json").read_text())
    assert document["pages"][0]["lines"][0]["vietocr_text"] == "Nợ trùng hạn"
    assert document["pages"][0]["lines"][0]["accentless_text"] == "no trung han"
    assert document["pages"][1]["lines"][0]["vietocr_text"] == ""
    assert index._validate_document(document, plan["documents"][0]) == document


def test_join_rejects_wrong_processed_dimensions() -> None:
    plan, batch, private_index, crops, proposal_payload = _fixture()
    proposal = json.loads(proposal_payload.splitlines()[0])
    proposal["processed_width"] += 10
    with pytest.raises(index.FamilyFirstSemanticIndexV1Error, match="dimensions"):
        index._line(
            private_index["samples"][0],
            batch["samples"][0],
            proposal,
            crops[0],
        )


def test_manifest_rejects_bool_as_integer_after_coherent_rehash(tmp_path: Path) -> None:
    plan, batch, private_index, crops, proposal_payload = _fixture()
    chunks = [tuple(crops), ()]
    original_open = (
        index.archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1
    )
    original_read = index.archive_v1.read_authenticated_family_first_semantic_label_chunk_v1
    try:
        index.archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1 = (
            lambda _cap: object()
        )
        index.archive_v1.read_authenticated_family_first_semantic_label_chunk_v1 = (
            lambda _session, **_kwargs: chunks.pop(0)
        )
        stage = tmp_path / "stage"
        stage.mkdir()
        manifest = index._build_index_stage(
            tmp_path,
            stage,
            object(),
            {"archive_id": "ffslav1:archive:" + "3" * 64},
            batch,
            plan,
            private_index,
            {"run_id": "ffvocrv1:run:" + "4" * 64},
            proposal_payload,
        )
    finally:
        index.archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1 = (
            original_open
        )
        index.archive_v1.read_authenticated_family_first_semantic_label_chunk_v1 = original_read
    tampered = copy.deepcopy(manifest)
    tampered["metrics"]["sample_count"] = True
    material = copy.deepcopy(tampered)
    material.pop("index_id")
    tampered["index_id"] = "ffsiv1:index:" + index.canonical_json_sha256_v1(material)
    with pytest.raises(index.FamilyFirstSemanticIndexV1Error, match="metrics"):
        index._validate_manifest(tampered)


def test_index_handle_rejects_raw_forged_copy_and_pickle() -> None:
    with pytest.raises(TypeError):
        index.AuthenticatedFamilyFirstSemanticIndexV1()
    value = index.AuthenticatedFamilyFirstSemanticIndexV1(index._MINT)
    with pytest.raises(TypeError):
        copy.copy(value)
    with pytest.raises(TypeError):
        copy.deepcopy(value)
    with pytest.raises(TypeError):
        pickle.dumps(value)
    forged = object.__new__(index.AuthenticatedFamilyFirstSemanticIndexV1)
    with pytest.raises(index.FamilyFirstSemanticIndexV1Error):
        index.project_authenticated_family_first_semantic_index_v1(forged)


def test_structure_projection_is_complete_and_provenance_blind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = {
        "document_id": "ffsiv1:document:" + "1" * 64,
        "document_ordinal": 7,
        "page_count": 1,
        "pages": [
            {
                "physical_page": 1,
                "lines": [
                    {
                        "line_ordinal": 0,
                        "source_bbox_raw_pixels": [1, 2, 30, 40],
                        "vietocr_text": "Tiền gửi khách hàng",
                    }
                ],
            }
        ],
        "private_provenance": {"bank": "SHOULD_NOT_LEAK"},
    }
    monkeypatch.setattr(
        index,
        "read_authenticated_family_first_semantic_document_v1",
        lambda _capability, **_kwargs: document,
    )
    projected = index.read_authenticated_family_first_structure_document_v1(
        object(), document_ordinal=7
    )
    assert projected == {
        "document_id": document["document_id"],
        "document_ordinal": 7,
        "page_count": 1,
        "pages": [
            {
                "lines": [
                    {
                        "bbox": [1, 2, 30, 40],
                        "source_line_index": 0,
                        "source_text": None,
                        "vietocr_text": "Tiền gửi khách hàng",
                    }
                ],
                "page_sequence": 1,
            }
        ],
    }
    assert "bank" not in repr(projected).lower()
