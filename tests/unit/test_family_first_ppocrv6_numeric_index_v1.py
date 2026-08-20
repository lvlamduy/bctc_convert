from __future__ import annotations

import copy
import hashlib
import io
import pickle
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v1 as index
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1


def _crop() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (80, 24), color=(255, 255, 255)).save(stream, format="PNG")
    return stream.getvalue()


def _proposal(ordinal: int, text: str) -> dict[str, object]:
    return runner._validate_result(
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
        receipt_payload=b"receipt",
        run_payload=b"run",
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


def test_numeric_document_join_is_source_ordered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index, "_live_index", lambda _cap: _state())
    document = index.read_authenticated_family_first_ppocrv6_numeric_document_v1(
        object(), document_ordinal=1
    )

    assert [line["raw_prediction"] for line in document["lines"]] == ["603.040.884", "–"]
    assert [line["line_ordinal"] for line in document["lines"]] == [5, 6]
    assert document["private_provenance"]["bank"] == "ACB"


def test_selected_batch_replays_crop_bound_typed_numeric_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    monkeypatch.setattr(index, "_live_index", lambda _cap: state)
    crops = [
        {
            "crop_png_bytes": _crop(),
            "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
            "sample_id": "sample-000000001",
        },
        {
            "crop_png_bytes": _crop(),
            "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
            "sample_id": "sample-000000002",
        },
    ]
    monkeypatch.setattr(
        index.archive_v1,
        "open_authenticated_family_first_semantic_label_reader_session_v1",
        lambda _archive: object(),
    )
    monkeypatch.setattr(
        index.archive_v1,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda _session, *, maximum_samples: tuple(crops[:maximum_samples]),
    )
    result = index.read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v1(
        object(),
        selections=(
            {"document_ordinal": 1, "line_ordinal": 5, "physical_page": 2},
            {"document_ordinal": 1, "line_ordinal": 6, "physical_page": 2},
        ),
    )

    assert result[0]["evidence"]["parsed_token"]["coefficient"] == 603_040_884
    assert result[1]["evidence"]["parsed_token"]["classification"] == "DASH_ZERO"
    assert result[1]["evidence"]["parsed_token"]["coefficient"] == 0
    assert result[0]["evidence"]["authority"]["accounting_closure_used_to_change_digits"] is False


def test_selection_is_exact_unique_and_source_ordered() -> None:
    valid = {"document_ordinal": 1, "line_ordinal": 5, "physical_page": 2}
    assert index._selections((valid,)) == ((1, 2, 5),)
    assert index._selections(({**valid, "line_ordinal": 0},)) == ((1, 2, 0),)
    for value in ([valid], ({**valid, "bank": "ACB"},), (valid, valid)):
        with pytest.raises(index.FamilyFirstPPocrV6NumericIndexV1Error):
            index._selections(value)


def test_capability_is_opaque_noncopyable_nonserializable() -> None:
    with pytest.raises(TypeError):
        index.AuthenticatedFamilyFirstPPocrV6NumericIndexV1()
    capability = index.AuthenticatedFamilyFirstPPocrV6NumericIndexV1(index._MINT)
    for action in (
        lambda: copy.copy(capability),
        lambda: copy.deepcopy(capability),
        lambda: pickle.dumps(capability),
    ):
        with pytest.raises(TypeError):
            action()


def test_git_ledger_allows_unrelated_source_change_on_clean_descendant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_commit = "a" * 40
    head = "b" * 40
    run_tree = "c" * 40
    payload = b"trusted implementation bytes"
    references = [
        {
            "path": path.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        for path in runner._TRUST_PATHS
    ]
    binding = {
        "commit": run_commit,
        "dirty": False,
        "implementation_refs": references,
        "source_tree_oid": run_tree,
    }
    monkeypatch.setattr(index.archive_v1, "_clean_head", lambda _root: head)
    monkeypatch.setattr(index, "_root_bytes", lambda *_args, **_kwargs: payload)

    def fake_git(_root: Path, *arguments: str) -> bytes:
        if arguments[:2] == ("merge-base", "--is-ancestor"):
            return b""
        if arguments[0] == "show":
            return payload
        if arguments == ("rev-parse", f"{run_commit}:src/bctc_ai"):
            return (run_tree + "\n").encode("ascii")
        raise AssertionError(arguments)

    monkeypatch.setattr(index.archive_v1, "_git", fake_git)
    assert index._git_ledger(tmp_path, binding) == head
