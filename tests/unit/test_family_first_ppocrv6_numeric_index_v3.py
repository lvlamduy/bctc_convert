from __future__ import annotations

import copy
import hashlib
import io
import pickle
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as index
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_sharded_runner_v3 as runner_v3
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


def test_numeric_v3_document_join_is_source_ordered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index, "_live_index", lambda _cap: _state())
    document = index.read_authenticated_family_first_ppocrv6_numeric_document_v3(
        object(), document_ordinal=1
    )

    assert [line["raw_prediction"] for line in document["lines"]] == ["603.040.884", "–"]
    assert [line["line_ordinal"] for line in document["lines"]] == [5, 6]
    assert document["private_provenance"]["bank"] == "ACB"


def test_selected_v3_batch_seeks_and_replays_crop_bound_evidence(
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
    result = index.read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v3(
        object(),
        selections=({"document_ordinal": 1, "line_ordinal": 6, "physical_page": 2},),
    )

    assert starts == [(session, 2)]
    assert result[0]["evidence"]["parsed_token"]["classification"] == "DASH_ZERO"
    assert result[0]["evidence"]["parsed_token"]["coefficient"] == 0


def test_v3_selection_is_exact_unique_and_source_ordered() -> None:
    valid = {"document_ordinal": 1, "line_ordinal": 5, "physical_page": 2}
    assert index._selections((valid,)) == ((1, 2, 5),)
    for value in ([valid], ({**valid, "bank": "ACB"},), (valid, valid)):
        with pytest.raises(index.FamilyFirstPPocrV6NumericIndexV3Error):
            index._selections(value)


def test_v3_capability_is_opaque_noncopyable_nonserializable() -> None:
    with pytest.raises(TypeError):
        index.AuthenticatedFamilyFirstPPocrV6NumericIndexV3()
    capability = index.AuthenticatedFamilyFirstPPocrV6NumericIndexV3(index._MINT)
    for action in (
        lambda: copy.copy(capability),
        lambda: copy.deepcopy(capability),
        lambda: pickle.dumps(capability),
    ):
        with pytest.raises(TypeError):
            action()


def test_v3_receipt_rejects_bool_as_int_and_self_rehash() -> None:
    metrics = {
        "document_count": 8,
        "empty_prediction_count": 0,
        "page_count": 100,
        "sample_count": 200,
        "shard_count": 1,
    }
    material = {
        "aggregate_id": "ffpnav3:aggregate:" + "1" * 64,
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
        "receipt_id": "ffpniv3:receipt:" + index.canonical_json_sha256_v1(material),
    }
    index._validate_receipt(receipt)
    attacked = copy.deepcopy(receipt)
    attacked["metrics"]["sample_count"] = True
    attacked_material = copy.deepcopy(attacked)
    attacked_material.pop("receipt_id")
    attacked["receipt_id"] = "ffpniv3:receipt:" + index.canonical_json_sha256_v1(attacked_material)
    with pytest.raises(index.FamilyFirstPPocrV6NumericIndexV3Error):
        index._validate_receipt(attacked)


def test_finalize_and_authenticate_v3_index_from_complete_shard_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/calibration").mkdir(parents=True)
    model = {
        "cache_directory": "PP-OCRv6_medium_rec",
        "enable_mkldnn": False,
        "repo_id": "PaddlePaddle/PP-OCRv6_medium_rec",
        "required_files": [
            {"path": f"model-{number}", "sha256": str(number) * 64, "size_bytes": number}
            for number in range(1, 4)
        ],
        "revision": "e5a92bcbc5cc1b494628e458d267778f0704fd7c",
    }
    crop = _crop()
    crop_sha = hashlib.sha256(crop).hexdigest()
    batch = {
        "batch_id": "ffslcv1:batch:" + "2" * 64,
        "sample_count": 2,
        "samples": [
            {
                "crop_ref": {"sha256": crop_sha, "size_bytes": len(crop)},
                "sample_id": f"sample-{ordinal:09d}",
            }
            for ordinal in (1, 2)
        ],
    }
    context = {
        "archive": object(),
        "batch": batch,
        "config_payload": b"config",
        "config_ref": {
            "path": runner_v3._CONFIG_PATH.as_posix(),
            "sha256": "c" * 64,
            "size_bytes": 6,
        },
        "git": {
            "commit": "a" * 40,
            "dirty": False,
            "implementation_refs": [],
            "source_tree_oid": "b" * 40,
        },
        "model": model,
        "model_cache": tmp_path,
        "projection": {
            "archive_id": "ffslav1:archive:" + "1" * 64,
            "batch_id": batch["batch_id"],
            "plan_id": "ffslpv1:plan:" + "3" * 64,
            "sample_count": 2,
        },
        "session": object(),
        "strict_git_head": True,
    }

    def execute(
        _root,
        _session,
        *,
        expected_sample_count,
        result_sink,
        first_sample_ordinal,
        require_archive_end,
        **_kwargs,
    ):
        for ordinal in range(first_sample_ordinal, first_sample_ordinal + expected_sample_count):
            result_sink(
                {
                    "crop_sha256": crop_sha,
                    "raw_prediction": "1" if ordinal == 1 else "–",
                    "reader_score": 0.9,
                    "sample_id": f"sample-{ordinal:09d}",
                }
            )
        return (
            {
                "accelerator": {
                    "compute_capability": [8, 9],
                    "device_name": "NVIDIA GeForce RTX 4090",
                },
                "device": "gpu:0",
                "model": copy.deepcopy(model),
                "packages": {
                    "paddleocr": "3.7.0",
                    "paddlepaddle-gpu": "3.3.0",
                },
                "precision": "fp32",
            },
            runner_v3._expected_counts(expected_sample_count, final_shard=require_archive_end),
            {"model_load_seconds": 1.0, "total_wall_seconds": 2.0},
        )

    monkeypatch.setattr(
        runner_v3.kernel_v1,
        "execute_authenticated_ppocrv6_numeric_reference_blind_v1",
        execute,
    )
    monkeypatch.setattr(runner_v3, "_assert_context", lambda *_args: None)
    runner_v3._run_shard(tmp_path, context, shard_ordinal=1)
    monkeypatch.setattr(runner_v3.runtime_v3, "_resolve_root", lambda value: value)
    monkeypatch.setattr(runner_v3, "_context", lambda *_args, **_kwargs: copy.deepcopy(context))
    runner_v3.aggregate_authenticated_family_first_ppocrv6_numeric_v3(
        tmp_path, object(), model_cache=tmp_path
    )

    archive_capability = object()
    plan = {
        "plan_id": context["projection"]["plan_id"],
        "documents": [{"page_count": 1}],
    }
    archive_payloads = (
        SimpleNamespace(root=tmp_path, model_cache=tmp_path),
        {"archive_id": context["projection"]["archive_id"]},
        batch,
        plan,
        {"samples": []},
    )
    monkeypatch.setattr(index.archive_v1, "_root", lambda value: value)
    monkeypatch.setattr(index.archive_v1, "_archive_payloads", lambda _capability: archive_payloads)

    receipt = index.finalize_authenticated_family_first_ppocrv6_numeric_index_v3(
        tmp_path, archive_capability, model_cache=tmp_path
    )
    capability = index.authenticate_family_first_ppocrv6_numeric_index_v3(
        tmp_path, archive_capability, model_cache=tmp_path
    )

    projection_distributions = []

    def project_model(_root, _cache, *, paddle_distribution):
        projection_distributions.append(paddle_distribution)
        return copy.deepcopy(model), tmp_path

    monkeypatch.setattr(index.runner_v3, "_git_ledger", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        index.runner_v3,
        "_configuration_ref",
        lambda _root: (b"config", copy.deepcopy(context["config_ref"])),
    )
    monkeypatch.setattr(index.kernel_v1, "_recognizer_projection", project_model)
    projection = index.project_authenticated_family_first_ppocrv6_numeric_index_v3(capability)

    assert receipt["metrics"] == {
        "document_count": 1,
        "empty_prediction_count": 0,
        "page_count": 1,
        "sample_count": 2,
        "shard_count": 1,
    }
    assert type(capability) is index.AuthenticatedFamilyFirstPPocrV6NumericIndexV3
    assert projection["metrics"] == receipt["metrics"]
    assert projection_distributions == ["paddlepaddle-gpu"]
