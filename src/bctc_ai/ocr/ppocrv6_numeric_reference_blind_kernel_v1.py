"""Reference-blind PP-OCRv6 recognizer kernel for financial-number crops.

Detection and recognition are intentionally separate.  This kernel receives
only immutable anonymous PNG crops selected by an authenticated table/geometry
layer.  It never receives a bank, filing, page, row label, period, unit,
expected value, accounting equation, family or schema identity.

The returned strings are raw proposals.  Conservative financial-token parsing
and all later corroboration remain separate evidence stages; in particular,
the kernel cannot repair a digit to make an accounting equation close.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import math
import os
import re
import socket
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from bctc_ai.evaluation import family_first_semantic_label_plan_v1 as plan_v1

__all__ = [
    "FamilyFirstPPocrV6NumericKernelV1Error",
    "recognize_reference_blind_numeric_crops_v1",
]


_SAMPLE_ID = re.compile(r"^numeric-sample-[0-9]{8}$")
_SAMPLE_FIELDS = {"crop_png_bytes", "crop_sha256", "sample_id"}
_RESULT_FIELDS = {"crop_sha256", "raw_prediction", "reader_score", "sample_id"}


class FamilyFirstPPocrV6NumericKernelV1Error(RuntimeError):
    """The anonymous crop batch, pinned recognizer, or provider output drifted."""


def _error(message: str) -> FamilyFirstPPocrV6NumericKernelV1Error:
    return FamilyFirstPPocrV6NumericKernelV1Error(message)


def _png_array(payload: bytes) -> np.ndarray:
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("reference-blind numeric crop is not one PNG snapshot")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            if image.width <= 0 or image.height <= 0:
                raise _error("reference-blind numeric crop dimensions drifted")
            # PaddleX accepts an in-memory ndarray.  BGR matches OpenCV/Paddle
            # conventions and avoids ever materializing a provider input path.
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            return np.ascontiguousarray(rgb[:, :, ::-1])
    except (OSError, ValueError) as exc:
        raise _error("reference-blind numeric crop cannot be decoded") from exc


def _samples(value: Any) -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    if type(value) is not tuple or not value:
        raise _error("numeric recognizer input must be one non-empty exact tuple")
    metadata: list[dict[str, Any]] = []
    images: list[np.ndarray] = []
    seen: set[str] = set()
    for expected_ordinal, raw in enumerate(value, 1):
        expected_id = f"numeric-sample-{expected_ordinal:08d}"
        if (
            type(raw) is not dict
            or set(raw) != _SAMPLE_FIELDS
            or type(raw["sample_id"]) is not str
            or _SAMPLE_ID.fullmatch(raw["sample_id"]) is None
            or raw["sample_id"] != expected_id
            or raw["sample_id"] in seen
            or type(raw["crop_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", raw["crop_sha256"])
            or type(raw["crop_png_bytes"]) is not bytes
        ):
            raise _error("reference-blind numeric sample identity/shape drifted")
        payload = raw["crop_png_bytes"]
        digest = hashlib.sha256(payload).hexdigest()
        if digest != raw["crop_sha256"]:
            raise _error("reference-blind numeric crop digest drifted")
        seen.add(raw["sample_id"])
        metadata.append({"crop_sha256": digest, "sample_id": raw["sample_id"]})
        images.append(_png_array(payload))
    return metadata, images


def _recognizer_projection(project_root: Path, model_cache: Path) -> tuple[dict[str, Any], Path]:
    try:
        runtime, _runtime_bytes = plan_v1._runtime(project_root.resolve())
        if (
            importlib.metadata.version("paddlepaddle") != runtime["paddlepaddle_version"]
            or importlib.metadata.version("paddleocr") != runtime["paddleocr_version"]
        ):
            raise _error("PP-OCRv6 numeric package runtime drifted")
        projection = plan_v1._model_projection(model_cache, runtime["numeric_recognizer"])
    except (
        plan_v1.FamilyFirstSemanticLabelPlanV1Error,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        raise _error("pinned PP-OCRv6 numeric recognizer cannot be authenticated") from exc
    if (
        projection["repo_id"] != "PaddlePaddle/PP-OCRv6_medium_rec"
        or projection["revision"] != "e5a92bcbc5cc1b494628e458d267778f0704fd7c"
        or projection["cache_directory"] != "PP-OCRv6_medium_rec"
        or projection["enable_mkldnn"] is not False
        or len(projection["required_files"]) != 3
    ):
        raise _error("PP-OCRv6 numeric recognizer identity/policy drifted")
    directory = model_cache.resolve() / "official_models" / projection["cache_directory"]
    return projection, directory


def _deny_network_connections() -> None:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise _error("network access is forbidden during PP-OCRv6 numeric inference")

    socket.socket.connect = denied  # type: ignore[method-assign]
    socket.create_connection = denied  # type: ignore[assignment]


def _load_recognizer(model_directory: Path, *, cpu_threads: int) -> Any:
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    _deny_network_connections()
    from paddleocr import TextRecognition

    return TextRecognition(
        model_name="PP-OCRv6_medium_rec",
        model_dir=os.fspath(model_directory),
        device="cpu",
        precision="fp32",
        enable_mkldnn=False,
        cpu_threads=cpu_threads,
    )


def _provider_result(value: Any) -> tuple[str, float]:
    wrapped = getattr(value, "json", None)
    if type(wrapped) is not dict or set(wrapped) != {"res"} or type(wrapped["res"]) is not dict:
        raise _error("PP-OCRv6 numeric provider wrapper drifted")
    payload = wrapped["res"]
    if set(payload) != {"input_path", "page_index", "rec_score", "rec_text"}:
        raise _error("PP-OCRv6 numeric provider fields drifted")
    score = payload["rec_score"]
    if (
        payload["input_path"] is not None
        or payload["page_index"] is not None
        or type(payload["rec_text"]) is not str
        or type(score) not in {int, float}
        or not math.isfinite(float(score))
        or not 0 <= float(score) <= 1
    ):
        raise _error("PP-OCRv6 numeric provider scalar contract drifted")
    return payload["rec_text"], float(score)


def recognize_reference_blind_numeric_crops_v1(
    project_root: Path,
    *,
    model_cache: Path,
    samples: tuple[dict[str, Any], ...],
    batch_size: int = 16,
    cpu_threads: int = 8,
) -> tuple[dict[str, Any], ...]:
    """Recognize one immutable anonymous crop batch with pinned PP-OCRv6.

    This function deliberately accepts no path, provenance, label, period,
    expected value, family or schema argument.  Its output is raw recognition
    evidence only.
    """

    if not isinstance(project_root, Path) or not isinstance(model_cache, Path):
        raise _error("project root and model cache must be pathlib Paths")
    if type(batch_size) is not int or batch_size <= 0:
        raise _error("numeric recognizer batch size must be one positive exact integer")
    if type(cpu_threads) is not int or cpu_threads <= 0:
        raise _error("numeric recognizer CPU threads must be one positive exact integer")
    metadata, images = _samples(samples)
    before, model_directory = _recognizer_projection(project_root, model_cache)
    recognizer = _load_recognizer(model_directory, cpu_threads=cpu_threads)
    after_load, _directory = _recognizer_projection(project_root, model_cache)
    if after_load != before:
        raise _error("PP-OCRv6 numeric model changed during load")
    results = recognizer.predict(input=images, batch_size=batch_size)
    if type(results) is not list or len(results) != len(metadata):
        raise _error("PP-OCRv6 numeric recognizer changed the crop denominator")
    records: list[dict[str, Any]] = []
    for sample, result in zip(metadata, results, strict=True):
        raw_text, score = _provider_result(result)
        record = {
            "crop_sha256": sample["crop_sha256"],
            "raw_prediction": raw_text,
            "reader_score": score,
            "sample_id": sample["sample_id"],
        }
        if set(record) != _RESULT_FIELDS:
            raise _error("PP-OCRv6 numeric result fields drifted")
        records.append(record)
    after, _directory = _recognizer_projection(project_root, model_cache)
    if after != before:
        raise _error("PP-OCRv6 numeric model changed during inference")
    return tuple(records)
