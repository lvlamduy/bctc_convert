from __future__ import annotations

import hashlib
import io
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive
from bctc_ai.ocr import ppocrv6_numeric_reference_blind_kernel_v1 as kernel


def _crop(color: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (80, 24), color=color).save(stream, format="PNG")
    return stream.getvalue()


def _sample(ordinal: int = 1, *, payload: bytes | None = None) -> dict[str, object]:
    crop = payload if payload is not None else _crop()
    return {
        "crop_png_bytes": crop,
        "crop_sha256": hashlib.sha256(crop).hexdigest(),
        "sample_id": f"numeric-sample-{ordinal:08d}",
    }


class _Result:
    def __init__(self, text: str, score: float = 0.999) -> None:
        self.json = {
            "res": {
                "input_path": None,
                "page_index": None,
                "rec_score": score,
                "rec_text": text,
            }
        }


class _Recognizer:
    def __init__(self, expected_batch_size: int = 4) -> None:
        self.calls = 0
        self.images = None
        self.expected_batch_size = expected_batch_size

    def predict(self, *, input, batch_size):
        self.calls += 1
        self.images = input
        assert batch_size == self.expected_batch_size
        values = ["603.040.884", "–", "1.234", "(55)"]
        return [
            _Result(values[index % len(values)], 0.99 - index / 100) for index in range(len(input))
        ]


def _model_projection() -> dict[str, object]:
    return {
        "cache_directory": "PP-OCRv6_medium_rec",
        "enable_mkldnn": False,
        "repo_id": "PaddlePaddle/PP-OCRv6_medium_rec",
        "required_files": [
            {"path": name, "sha256": str(index) * 64, "size_bytes": index}
            for index, name in enumerate(
                ["inference.json", "inference.pdiparams", "inference.yml"], 1
            )
        ],
        "revision": "e5a92bcbc5cc1b494628e458d267778f0704fd7c",
    }


def test_private_model_snapshot_consumes_only_verified_bytes(tmp_path: Path) -> None:
    source = tmp_path / "model"
    source.mkdir()
    required = []
    for index, name in enumerate(["inference.json", "inference.pdiparams", "inference.yml"], 1):
        payload = f"payload-{index}".encode()
        (source / name).write_bytes(payload)
        required.append(
            {
                "path": f"MODEL_CACHE/official_models/PP-OCRv6_medium_rec/{name}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    projection = {**_model_projection(), "required_files": required}
    snapshot = kernel._materialize_private_model_snapshot(source, projection)
    try:
        assert snapshot.stat().st_mode & 0o777 == 0o700
        assert sorted(item.name for item in snapshot.iterdir()) == sorted(
            ["inference.json", "inference.pdiparams", "inference.yml"]
        )
        for reference in required:
            name = Path(reference["path"]).name
            assert hashlib.sha256((snapshot / name).read_bytes()).hexdigest() == reference["sha256"]
            assert (snapshot / name).stat().st_ino != (source / name).stat().st_ino
    finally:
        shutil.rmtree(snapshot)


def test_kernel_is_reference_blind_and_preserves_exact_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    recognizer = _Recognizer()
    calls = 0

    def projection(_root, _cache):
        nonlocal calls
        calls += 1
        return _model_projection(), tmp_path / "PP-OCRv6_medium_rec"

    monkeypatch.setattr(kernel, "_recognizer_projection", projection)
    monkeypatch.setattr(kernel, "_load_recognizer", lambda *_args, **_kwargs: recognizer)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    monkeypatch.setattr(kernel, "_materialize_private_model_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        kernel.importlib.metadata,
        "version",
        lambda name: {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"}[name],
    )
    records = kernel.recognize_reference_blind_numeric_crops_v1(
        tmp_path,
        model_cache=tmp_path,
        samples=(_sample(1), _sample(2, payload=_crop((250, 250, 250)))),
        batch_size=4,
        cpu_threads=2,
    )

    assert calls == 3
    assert recognizer.calls == 1
    assert len(recognizer.images) == 2
    assert records[0]["sample_id"] == "numeric-sample-00000001"
    assert records[0]["raw_prediction"] == "603.040.884"
    assert records[1]["raw_prediction"] == "–"
    serialized = repr((recognizer.images, records)).lower()
    for forbidden in (
        "bank",
        "filing",
        "page",
        "period",
        "unit",
        "family",
        "report_norm",
        "expected",
        "accounting",
    ):
        assert forbidden not in serialized


def test_stream_kernel_loads_once_and_exhausts_exact_archive_axis(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    recognizer = _Recognizer(expected_batch_size=2)
    projection_calls = 0
    chunks = [
        (
            {
                "crop_png_bytes": _crop(),
                "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
                "sample_id": "sample-000000001",
            },
            {
                "crop_png_bytes": _crop((250, 250, 250)),
                "crop_sha256": hashlib.sha256(_crop((250, 250, 250))).hexdigest(),
                "sample_id": "sample-000000002",
            },
            {
                "crop_png_bytes": _crop((245, 245, 245)),
                "crop_sha256": hashlib.sha256(_crop((245, 245, 245))).hexdigest(),
                "sample_id": "sample-000000003",
            },
        ),
        (),
    ]

    def projection(_root, _cache):
        nonlocal projection_calls
        projection_calls += 1
        return _model_projection(), tmp_path / "PP-OCRv6_medium_rec"

    monkeypatch.setattr(kernel, "_recognizer_projection", projection)
    monkeypatch.setattr(kernel, "_load_recognizer", lambda *_args, **_kwargs: recognizer)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    monkeypatch.setattr(kernel, "_materialize_private_model_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        kernel.importlib.metadata,
        "version",
        lambda name: {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"}[name],
    )
    monkeypatch.setattr(
        kernel,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda _session, *, maximum_samples: chunks.pop(0),
    )
    monkeypatch.setattr(
        kernel,
        "_seek_authenticated_archive_reader_v1",
        lambda _session, *, first_sample_ordinal: (
            3 if first_sample_ordinal == 1 else pytest.fail("unexpected shard start")
        ),
    )
    records = []
    runtime, counts, metrics = kernel.execute_authenticated_ppocrv6_numeric_reference_blind_v1(
        tmp_path,
        object(),
        expected_sample_count=3,
        model_cache=tmp_path,
        result_sink=records.append,
        batch_size=2,
        cpu_threads=2,
    )

    assert projection_calls == 3
    assert recognizer.calls == 2
    assert [item["sample_id"] for item in records] == [
        "sample-000000001",
        "sample-000000002",
        "sample-000000003",
    ]
    assert counts == {
        "formal_run_count": 1,
        "model_build_count": 1,
        "reader_chunk_call_count": 2,
        "recognizer_predict_call_count": 2,
        "result_count": 3,
    }
    assert runtime["device"] == "cpu"
    assert runtime["precision"] == "fp32"
    assert metrics["total_wall_seconds"] >= metrics["model_load_seconds"] >= 0


def test_stream_kernel_emits_global_ids_for_one_nonfinal_shard(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    recognizer = _Recognizer(expected_batch_size=2)
    chunks = [
        (
            {
                "crop_png_bytes": _crop(),
                "crop_sha256": hashlib.sha256(_crop()).hexdigest(),
                "sample_id": "sample-000000004",
            },
            {
                "crop_png_bytes": _crop((250, 250, 250)),
                "crop_sha256": hashlib.sha256(_crop((250, 250, 250))).hexdigest(),
                "sample_id": "sample-000000005",
            },
        )
    ]
    monkeypatch.setattr(
        kernel,
        "_recognizer_projection",
        lambda *_args: (_model_projection(), tmp_path / "PP-OCRv6_medium_rec"),
    )
    monkeypatch.setattr(kernel, "_load_recognizer", lambda *_args, **_kwargs: recognizer)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    monkeypatch.setattr(kernel, "_materialize_private_model_snapshot", lambda *_args: snapshot)
    monkeypatch.setattr(
        kernel.importlib.metadata,
        "version",
        lambda name: {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"}[name],
    )
    monkeypatch.setattr(
        kernel,
        "_seek_authenticated_archive_reader_v1",
        lambda _session, *, first_sample_ordinal: (
            10 if first_sample_ordinal == 4 else pytest.fail("unexpected shard start")
        ),
    )
    monkeypatch.setattr(
        kernel,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda _session, *, maximum_samples: chunks.pop(0),
    )
    records = []
    _runtime, counts, _metrics = kernel.execute_authenticated_ppocrv6_numeric_reference_blind_v1(
        tmp_path,
        object(),
        expected_sample_count=2,
        model_cache=tmp_path,
        result_sink=records.append,
        batch_size=2,
        cpu_threads=2,
        first_sample_ordinal=4,
        require_archive_end=False,
    )

    assert [item["sample_id"] for item in records] == [
        "sample-000000004",
        "sample-000000005",
    ]
    assert counts["reader_chunk_call_count"] == 1


def test_stream_kernel_rejects_nonfinal_archive_end_claim(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        kernel,
        "_seek_authenticated_archive_reader_v1",
        lambda _session, *, first_sample_ordinal: 10,
    )
    with pytest.raises(
        kernel.FamilyFirstPPocrV6NumericKernelV1Error,
        match="archive-end assertion",
    ):
        kernel.execute_authenticated_ppocrv6_numeric_reference_blind_v1(
            tmp_path,
            object(),
            expected_sample_count=2,
            model_cache=tmp_path,
            result_sink=lambda _value: None,
            first_sample_ordinal=4,
            require_archive_end=True,
        )


def test_archive_seek_accounts_for_magic_and_can_reset_sealed_session() -> None:
    crops = (b"first", b"second", b"third")
    temporary = tempfile.TemporaryFile()
    descriptor = os.dup(temporary.fileno())
    os.write(descriptor, archive._MAGIC)
    for crop in crops:
        os.write(descriptor, archive._FRAME.pack(len(crop)))
        os.write(descriptor, crop)
    batch = {
        "sample_count": len(crops),
        "samples": [
            {
                "crop_ref": {
                    "sha256": hashlib.sha256(crop).hexdigest(),
                    "size_bytes": len(crop),
                },
                "sample_id": f"sample-{ordinal:09d}",
            }
            for ordinal, crop in enumerate(crops, 1)
        ],
    }
    session = archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1(archive._MINT)
    archive._SESSIONS[session] = archive._SessionState(
        descriptor=descriptor,
        batch=batch,
        cursor=0,
        offset=len(archive._MAGIC),
        archive=object(),
    )
    try:
        assert kernel._seek_authenticated_archive_reader_v1(session, first_sample_ordinal=2) == len(
            crops
        )
        assert (
            archive.read_authenticated_family_first_semantic_label_chunk_v1(
                session, maximum_samples=1
            )[0]["sample_id"]
            == "sample-000000002"
        )
        assert kernel._seek_authenticated_archive_reader_v1(session, first_sample_ordinal=1) == len(
            crops
        )
        assert (
            archive.read_authenticated_family_first_semantic_label_chunk_v1(
                session, maximum_samples=1
            )[0]["sample_id"]
            == "sample-000000001"
        )
    finally:
        archive._SESSIONS.pop(session, None)
        os.close(descriptor)
        temporary.close()


@pytest.mark.parametrize(
    "samples",
    [
        [_sample()],
        (_sample(2),),
        ({**_sample(), "bank": "ACB"},),
        ({**_sample(), "crop_sha256": "0" * 64},),
        ({**_sample(), "crop_png_bytes": bytearray(_crop())},),
    ],
)
def test_kernel_rejects_nonexact_or_context_bearing_batch(samples) -> None:
    with pytest.raises(kernel.FamilyFirstPPocrV6NumericKernelV1Error):
        kernel.recognize_reference_blind_numeric_crops_v1(
            Path("."),
            model_cache=Path("."),
            samples=samples,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"input_path": "/tmp/crop.png", "page_index": None, "rec_score": 0.9, "rec_text": "1"},
        {"input_path": None, "page_index": 0, "rec_score": 0.9, "rec_text": "1"},
        {"input_path": None, "page_index": None, "rec_score": True, "rec_text": "1"},
        {"input_path": None, "page_index": None, "rec_score": float("nan"), "rec_text": "1"},
        {"input_path": None, "page_index": None, "rec_score": 0.9, "rec_text": 1},
    ],
)
def test_provider_paths_and_scalar_coercions_reject(payload) -> None:
    result = type("Result", (), {"json": {"res": payload}})()
    with pytest.raises(kernel.FamilyFirstPPocrV6NumericKernelV1Error):
        kernel._provider_result(result)
