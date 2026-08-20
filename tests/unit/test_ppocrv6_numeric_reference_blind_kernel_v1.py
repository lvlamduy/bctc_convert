from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

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
    def __init__(self) -> None:
        self.calls = 0
        self.images = None

    def predict(self, *, input, batch_size):
        self.calls += 1
        self.images = input
        assert batch_size == 4
        return [_Result("603.040.884"), _Result("–", 0.91)]


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
