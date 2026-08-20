from __future__ import annotations

import copy
import hashlib
import io
import pickle
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v2 as index
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _crop() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (80, 24), color=(255, 255, 255)).save(stream, format="PNG")
    return stream.getvalue()


def _proposal(ordinal: int, text: str) -> dict[str, object]:
    return runner_v1._validate_result(
        {
            "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
            "raw_prediction": text,
            "reader_score": 0.99,
            "sample_id": f"sample-{ordinal:09d}",
        },
        ordinal,
    )


def _state() -> tuple[object, dict, dict, dict, dict]:
    proposals = [_proposal(1, "603.040.884"), _proposal(2, "–")]
    payload = b"".join(canonical_json_bytes_v1(item) for item in proposals)
    first_size = len(canonical_json_bytes_v1(proposals[0]))
    fake = index._IndexState(
        root=Path("."),
        archive=object(),
        model_cache=Path("models"),
        receipt_payload=b"receipt",
        aggregate_payload=b"aggregate",
        proposal_payload=payload,
        offsets=((0, first_size), (first_size, len(payload))),
    )
    crop_ref = {
        "path": "opaque.png",
        "sha256": hashlib.sha256(_crop()).hexdigest(),
        "size_bytes": len(_crop()),
    }
    batch = {
        "samples": [
            {"crop_ref": copy.deepcopy(crop_ref), "sample_id": "sample-000000001"},
            {"crop_ref": copy.deepcopy(crop_ref), "sample_id": "sample-000000002"},
        ]
    }
    private = {
        "samples": [
            {
                "document_ordinal": 1,
                "line_ordinal": 5,
                "physical_page": 2,
                "sample_id": "sample-000000001",
                "source_bbox_raw_pixels": [10, 20, 80, 40],
            },
            {
                "document_ordinal": 1,
                "line_ordinal": 6,
                "physical_page": 2,
                "sample_id": "sample-000000002",
                "source_bbox_raw_pixels": [90, 20, 150, 40],
            },
        ]
    }
    plan = {
        "documents": [
            {
                "private_provenance": {
                    "bank": "ACB",
                    "period": "Q1",
                    "scope": "CONSOLIDATED",
                    "year": 2026,
                },
                "source_pdf_ref": {"path": "source.pdf", "sha256": "1" * 64, "size_bytes": 1},
            }
        ]
    }
    receipt = {"metrics": {"document_count": 1}}
    return fake, receipt, batch, plan, private


def test_numeric_v2_document_join_is_source_ordered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index, "_live_index", lambda _cap: _state())
    document = index.read_authenticated_family_first_ppocrv6_numeric_document_v2(
        object(), document_ordinal=1
    )

    assert [line["raw_prediction"] for line in document["lines"]] == ["603.040.884", "–"]
    assert [line["line_ordinal"] for line in document["lines"]] == [5, 6]
    assert document["private_provenance"]["bank"] == "ACB"


def test_selected_v2_batch_seeks_and_replays_crop_bound_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    monkeypatch.setattr(index, "_live_index", lambda _cap: state)
    crop = {
        "crop_png_bytes": _crop(),
        "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
        "sample_id": "sample-000000002",
    }
    session = object()
    monkeypatch.setattr(
        index.archive_v1,
        "open_authenticated_family_first_semantic_label_reader_session_v1",
        lambda _archive: session,
    )
    starts = []
    monkeypatch.setattr(
        index.kernel_v1,
        "_seek_authenticated_archive_reader_v1",
        lambda supplied, *, first_sample_ordinal: starts.append((supplied, first_sample_ordinal)),
    )
    monkeypatch.setattr(
        index.archive_v1,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda supplied, *, maximum_samples: (crop,),
    )
    result = index.read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v2(
        object(),
        selections=({"document_ordinal": 1, "line_ordinal": 6, "physical_page": 2},),
    )

    assert starts == [(session, 2)]
    assert result[0]["evidence"]["parsed_token"]["classification"] == "DASH_ZERO"
    assert result[0]["evidence"]["parsed_token"]["coefficient"] == 0


def test_v2_selection_is_exact_unique_and_source_ordered() -> None:
    valid = {"document_ordinal": 1, "line_ordinal": 5, "physical_page": 2}
    assert index._selections((valid,)) == ((1, 2, 5),)
    for value in ([valid], ({**valid, "bank": "ACB"},), (valid, valid)):
        with pytest.raises(index.FamilyFirstPPocrV6NumericIndexV2Error):
            index._selections(value)


def test_v2_capability_is_opaque_noncopyable_nonserializable() -> None:
    with pytest.raises(TypeError):
        index.AuthenticatedFamilyFirstPPocrV6NumericIndexV2()
    capability = index.AuthenticatedFamilyFirstPPocrV6NumericIndexV2(index._MINT)
    for action in (
        lambda: copy.copy(capability),
        lambda: copy.deepcopy(capability),
        lambda: pickle.dumps(capability),
    ):
        with pytest.raises(TypeError):
            action()


def test_v2_receipt_rejects_bool_as_int_and_self_rehash() -> None:
    metrics = {
        "document_count": 8,
        "empty_prediction_count": 0,
        "page_count": 100,
        "sample_count": 200,
        "shard_count": 1,
    }
    material = {
        "aggregate_id": "ffpnav2:aggregate:" + "1" * 64,
        "aggregate_ref": {"path": "a.json", "sha256": "2" * 64, "size_bytes": 1},
        "archive_id": "ffslav1:archive:" + "3" * 64,
        "authority": copy.deepcopy(index._AUTHORITY),
        "batch_id": "ffslcv1:batch:" + "4" * 64,
        "format_version": index.FORMAT_VERSION,
        "metrics": metrics,
        "numeric_axis_sha256": "5" * 64,
        "plan_id": "ffslpv1:plan:" + "6" * 64,
        "proposal_ref": {"path": "b.jsonl", "sha256": "7" * 64, "size_bytes": 1},
        "state": "VERIFIED_COMPLETE_ORDERED_SHARDED_PPOCRV6_NUMERIC_PROPOSAL_AXIS",
    }
    receipt = {
        **material,
        "receipt_id": "ffpniv2:receipt:" + index.canonical_json_sha256_v1(material),
    }
    index._validate_receipt(receipt)
    attacked = copy.deepcopy(receipt)
    attacked["metrics"]["sample_count"] = True
    attacked_material = copy.deepcopy(attacked)
    attacked_material.pop("receipt_id")
    attacked["receipt_id"] = "ffpniv2:receipt:" + index.canonical_json_sha256_v1(attacked_material)
    with pytest.raises(index.FamilyFirstPPocrV6NumericIndexV2Error):
        index._validate_receipt(attacked)
