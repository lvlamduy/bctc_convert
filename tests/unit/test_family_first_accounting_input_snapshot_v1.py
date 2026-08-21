from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from bctc_ai.evaluation import family_first_accounting_input_snapshot_v1 as snapshot
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _live_state():
    state = SimpleNamespace(name="state")
    receipt = {"metrics": {"document_count": 2}}
    crop_ref = {"path": "opaque.png", "sha256": "1" * 64, "size_bytes": 10}
    batch = {
        "samples": [
            {"crop_ref": copy.deepcopy(crop_ref), "sample_id": f"sample-{ordinal:09d}"}
            for ordinal in (1, 2, 3)
        ]
    }
    plan = {
        "documents": [
            {
                "private_provenance": {"opaque_filing": "one"},
                "source_pdf_ref": {"path": "one.pdf", "sha256": "2" * 64, "size_bytes": 20},
            },
            {
                "private_provenance": {"opaque_filing": "two"},
                "source_pdf_ref": {"path": "two.pdf", "sha256": "3" * 64, "size_bytes": 30},
            },
        ]
    }
    private = {
        "samples": [
            {
                "document_ordinal": 1,
                "line_ordinal": 0,
                "physical_page": 1,
                "sample_id": "sample-000000001",
                "source_bbox_raw_pixels": [1, 2, 30, 20],
            },
            {
                "document_ordinal": 1,
                "line_ordinal": 1,
                "physical_page": 1,
                "sample_id": "sample-000000002",
                "source_bbox_raw_pixels": [31, 2, 60, 20],
            },
            {
                "document_ordinal": 2,
                "line_ordinal": 0,
                "physical_page": 1,
                "sample_id": "sample-000000003",
                "source_bbox_raw_pixels": [1, 2, 30, 20],
            },
        ]
    }
    return state, receipt, batch, plan, private


def _proposal(ordinal: int):
    return {
        "crop_sha256": "1" * 64,
        "raw_prediction": str(ordinal * 100),
        "reader_score": 0.9,
        "sample_id": f"sample-{ordinal:09d}",
    }


def test_numeric_documents_are_read_once_in_source_order(monkeypatch: pytest.MonkeyPatch) -> None:
    live = _live_state()
    calls = []
    monkeypatch.setattr(
        snapshot.numeric_v3,
        "_live_index",
        lambda _capability: calls.append(True) or live,
    )
    monkeypatch.setattr(
        snapshot.numeric_v3, "_proposal_at", lambda _state, ordinal: _proposal(ordinal)
    )

    documents = snapshot.read_authenticated_family_first_numeric_documents_snapshot_v1(
        object(), document_ordinals=(1, 2)
    )

    assert len(calls) == 2
    assert [document["document_ordinal"] for document in documents] == [1, 2]
    assert [line["raw_prediction"] for line in documents[0]["lines"]] == ["100", "200"]
    assert [line["sample_id"] for line in documents[1]["lines"]] == ["sample-000000003"]


@pytest.mark.parametrize("ordinals", ([], (True,), (1.0,), (0,), (3,), (2, 1), (1, 1)))
def test_numeric_document_snapshot_requires_exact_source_ordered_tuple(ordinals) -> None:
    with pytest.raises(snapshot.FamilyFirstAccountingInputSnapshotV1Error, match="snapshot"):
        snapshot._document_ordinals(ordinals, document_count=2)


def test_numeric_document_snapshot_rejects_live_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _live_state()
    changed = copy.deepcopy(first)
    changed[4]["samples"][0]["source_bbox_raw_pixels"][0] = 2
    responses = [first, changed]
    monkeypatch.setattr(snapshot.numeric_v3, "_live_index", lambda _capability: responses.pop(0))
    monkeypatch.setattr(
        snapshot.numeric_v3, "_proposal_at", lambda _state, ordinal: _proposal(ordinal)
    )

    with pytest.raises(snapshot.FamilyFirstAccountingInputSnapshotV1Error, match="changed"):
        snapshot.read_authenticated_family_first_numeric_documents_snapshot_v1(
            object(), document_ordinals=(1,)
        )


def _semantic_live():
    documents = [
        {"document_id": "document-one", "document_ordinal": 1},
        {"document_id": "document-two", "document_ordinal": 2},
    ]
    state = SimpleNamespace(root="root", plan_documents_payload=b"plan")
    manifest = {
        "documents": [
            {
                "content_ref": {
                    "path": f"document-{ordinal:04d}.json",
                    "sha256": str(ordinal) * 64,
                    "size_bytes": 10,
                },
                "document_id": document["document_id"],
            }
            for ordinal, document in enumerate(documents, 1)
        ],
        "metrics": {"document_count": 2},
    }
    payloads = {
        f"document-{ordinal:04d}.json": canonical_json_bytes_v1(document)
        for ordinal, document in enumerate(documents, 1)
    }
    return state, manifest, documents, payloads


def _patch_semantic(monkeypatch: pytest.MonkeyPatch, *, payload_reader):
    state, manifest, documents, payloads = _semantic_live()
    live_calls = []
    monkeypatch.setattr(
        snapshot.semantic_v1,
        "_live_index",
        lambda _capability: live_calls.append(True) or (state, manifest),
    )
    monkeypatch.setattr(snapshot.semantic_v1, "_root_bytes", payload_reader(payloads))
    monkeypatch.setattr(snapshot.semantic_v1, "_matches", lambda *_args: None)
    monkeypatch.setattr(
        snapshot.semantic_v1,
        "_canonical_object",
        lambda payload, _label: (
            {"documents": [{}, {}]} if payload == b"plan" else json.loads(payload)
        ),
    )
    monkeypatch.setattr(
        snapshot.semantic_v1,
        "_validate_document",
        lambda document, _expected: copy.deepcopy(document),
    )
    return state, manifest, documents, payloads, live_calls


def test_semantic_documents_are_read_and_reread_in_one_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_paths = []

    def reader(payloads):
        def read(_root, path, _label):
            read_paths.append(path)
            return payloads[path]

        return read

    _state, _manifest, documents, _payloads, live_calls = _patch_semantic(
        monkeypatch, payload_reader=reader
    )

    result = snapshot.read_authenticated_family_first_semantic_documents_snapshot_v1(
        object(), document_ordinals=(1, 2)
    )

    assert result == tuple(documents)
    assert read_paths == [
        "document-0001.json",
        "document-0002.json",
        "document-0001.json",
        "document-0002.json",
    ]
    assert len(live_calls) == 2


def test_semantic_document_snapshot_rejects_mid_read_byte_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def reader(payloads):
        def read(_root, path, _label):
            nonlocal calls
            calls += 1
            if calls == 3:
                return payloads[path] + b" "
            return payloads[path]

        return read

    _patch_semantic(monkeypatch, payload_reader=reader)

    with pytest.raises(snapshot.FamilyFirstAccountingInputSnapshotV1Error, match="changed"):
        snapshot.read_authenticated_family_first_semantic_documents_snapshot_v1(
            object(), document_ordinals=(1, 2)
        )


def test_semantic_snapshot_final_validation_rejects_consumed_document_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = False

    def reader(payloads):
        def read(_root, path, _label):
            return payloads[path] + (b" " if changed else b"")

        return read

    _state, _manifest, documents, _payloads, _live_calls = _patch_semantic(
        monkeypatch, payload_reader=reader
    )
    snapshot.validate_authenticated_family_first_semantic_documents_snapshot_v1(
        object(), tuple(documents)
    )
    changed = True
    with pytest.raises(snapshot.FamilyFirstAccountingInputSnapshotV1Error, match="changed"):
        snapshot.validate_authenticated_family_first_semantic_documents_snapshot_v1(
            object(), tuple(documents)
        )
