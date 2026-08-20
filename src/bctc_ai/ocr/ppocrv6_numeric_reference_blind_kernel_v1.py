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
import shutil
import socket
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.evaluation import family_first_semantic_label_plan_v1 as plan_v1
from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (
    AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    read_authenticated_family_first_semantic_label_chunk_v1,
)

__all__ = [
    "FamilyFirstPPocrV6NumericKernelV1Error",
    "execute_authenticated_ppocrv6_numeric_reference_blind_v1",
    "recognize_reference_blind_numeric_crops_v1",
]


_SAMPLE_ID = re.compile(r"^numeric-sample-[0-9]{8}$")
_ARCHIVE_SAMPLE_ID = re.compile(r"^sample-[0-9]{9}$")
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


def _samples(
    value: Any, *, first_ordinal: int = 1, archive_axis: bool = False
) -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    if type(value) is not tuple or not value:
        raise _error("numeric recognizer input must be one non-empty exact tuple")
    metadata: list[dict[str, Any]] = []
    images: list[np.ndarray] = []
    seen: set[str] = set()
    if type(first_ordinal) is not int or first_ordinal <= 0 or type(archive_axis) is not bool:
        raise _error("numeric recognizer anonymous sample-axis policy drifted")
    for expected_ordinal, raw in enumerate(value, first_ordinal):
        expected_id = (
            f"sample-{expected_ordinal:09d}"
            if archive_axis
            else f"numeric-sample-{expected_ordinal:08d}"
        )
        pattern = _ARCHIVE_SAMPLE_ID if archive_axis else _SAMPLE_ID
        if (
            type(raw) is not dict
            or set(raw) != _SAMPLE_FIELDS
            or type(raw["sample_id"]) is not str
            or pattern.fullmatch(raw["sample_id"]) is None
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


def _seek_authenticated_archive_reader_v1(
    session: AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    *,
    first_sample_ordinal: int,
) -> int:
    """Seek one sealed reader to a fixed global sample ordinal.

    The complete archive manifest already binds every frame size and crop hash.
    Sharded recognition must not reread a multi-gigabyte prefix for every
    shard, so the offset is derived from that closed public frame axis and
    checked against the archive descriptor before the session cursor moves.
    A shard orchestrator may safely reset the same immutable session between
    completed shards; no provider output or partial shard state is reused.
    Every selected frame is still read and hash-verified by the ordinary chunk
    accessor; the final shard aggregate proves complete contiguous coverage.
    """

    if type(session) is not AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
        raise _error("one exact authenticated archive reader session is required")
    state = archive_v1._SESSIONS.get(session)
    if state is None:
        raise _error("numeric shard reader session is not live")
    if type(first_sample_ordinal) is not int or first_sample_ordinal <= 0:
        raise _error("numeric shard first sample ordinal must be one positive integer")
    total = state.batch["sample_count"]
    if type(total) is not int or not 1 <= first_sample_ordinal <= total:
        raise _error("numeric shard first sample lies outside the archive denominator")
    sizes = [sample["crop_ref"]["size_bytes"] for sample in state.batch["samples"]]
    if (
        len(sizes) != total
        or any(type(size) is not int or size <= 0 for size in sizes)
        or os.fstat(state.descriptor).st_size
        != len(archive_v1._MAGIC) + sum(archive_v1._FRAME.size + size for size in sizes)
    ):
        raise _error("numeric shard archive frame-size axis drifted")
    start_index = first_sample_ordinal - 1
    offset = len(archive_v1._MAGIC) + sum(
        archive_v1._FRAME.size + size for size in sizes[:start_index]
    )
    encoded = os.pread(state.descriptor, archive_v1._FRAME.size, offset)
    if (
        len(encoded) != archive_v1._FRAME.size
        or archive_v1._FRAME.unpack(encoded)[0] != sizes[start_index]
    ):
        raise _error("numeric shard archive seek target differs from its frame manifest")
    state.cursor = start_index
    state.offset = offset
    return total


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


def _write_snapshot_file(directory: Path, name: str, payload: bytes) -> None:
    descriptor = os.open(
        directory / name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise _error("private numeric model snapshot write made no progress")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _materialize_private_model_snapshot(model_directory: Path, projection: dict[str, Any]) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="family-first-ppocrv6-numeric-model-"))
    os.chmod(stage, 0o700)
    try:
        for reference in projection["required_files"]:
            name = Path(reference["path"]).name
            payload, _metadata = plan_v1._stable_bytes(
                model_directory / name, f"PP-OCRv6 numeric model source {name}"
            )
            if (
                len(payload) != reference["size_bytes"]
                or hashlib.sha256(payload).hexdigest() != reference["sha256"]
            ):
                raise _error("PP-OCRv6 numeric model changed before private snapshot")
            _write_snapshot_file(stage, name, payload)
        descriptor = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return stage
    except BaseException:
        shutil.rmtree(stage)
        raise


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
    snapshot = _materialize_private_model_snapshot(model_directory, before)
    try:
        recognizer = _load_recognizer(snapshot, cpu_threads=cpu_threads)
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
    finally:
        shutil.rmtree(snapshot)


def execute_authenticated_ppocrv6_numeric_reference_blind_v1(
    project_root: Path,
    reader_session: AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    *,
    expected_sample_count: int,
    model_cache: Path,
    result_sink: Callable[[dict[str, Any]], None],
    batch_size: int = 64,
    cpu_threads: int = 16,
    first_sample_ordinal: int = 1,
    require_archive_end: bool = True,
) -> tuple[dict[str, Any], dict[str, int], dict[str, float]]:
    """Stream one exact contiguous archive range through one recognizer load.

    Defaults retain the V1 complete-axis contract.  The range controls exist
    for the V2 shard orchestrator: every shard receives a fresh sealed archive
    reader, seeks by the closed frame-size axis, and emits global sample IDs.
    Only the final shard is allowed to assert archive exhaustion.
    """

    if not isinstance(project_root, Path) or not isinstance(model_cache, Path):
        raise _error("project root and model cache must be pathlib Paths")
    if type(expected_sample_count) is not int or expected_sample_count <= 0:
        raise _error("numeric reader expected denominator must be one positive exact integer")
    if not callable(result_sink):
        raise _error("numeric reader result sink must be callable")
    if type(batch_size) is not int or not 1 <= batch_size <= 512:
        raise _error("numeric reader batch size must be one exact integer in [1,512]")
    if type(cpu_threads) is not int or not 1 <= cpu_threads <= 64:
        raise _error("numeric reader CPU threads must be one exact integer in [1,64]")
    if type(first_sample_ordinal) is not int or first_sample_ordinal <= 0:
        raise _error("numeric reader first sample ordinal must be one positive integer")
    if type(require_archive_end) is not bool:
        raise _error("numeric reader archive-end policy must be one exact boolean")

    archive_sample_count = _seek_authenticated_archive_reader_v1(
        reader_session,
        first_sample_ordinal=first_sample_ordinal,
    )
    last_sample_ordinal = first_sample_ordinal + expected_sample_count - 1
    if last_sample_ordinal > archive_sample_count:
        raise _error("numeric reader shard exceeds the authenticated archive denominator")
    if require_archive_end and last_sample_ordinal != archive_sample_count:
        raise _error("numeric reader archive-end assertion is not on the final sample")

    started = time.perf_counter()
    before, model_directory = _recognizer_projection(project_root, model_cache)
    snapshot = _materialize_private_model_snapshot(model_directory, before)
    model_started = time.perf_counter()
    try:
        recognizer = _load_recognizer(snapshot, cpu_threads=cpu_threads)
        model_load_seconds = time.perf_counter() - model_started
        after_load, _directory = _recognizer_projection(project_root, model_cache)
        if after_load != before:
            raise _error("PP-OCRv6 numeric model changed during load")

        counts = {
            "formal_run_count": 1,
            "model_build_count": 1,
            "reader_chunk_call_count": 0,
            "recognizer_predict_call_count": 0,
            "result_count": 0,
        }
        cursor = 0
        while cursor < expected_sample_count:
            maximum = min(4096, expected_sample_count - cursor)
            chunk = read_authenticated_family_first_semantic_label_chunk_v1(
                reader_session, maximum_samples=maximum
            )
            counts["reader_chunk_call_count"] += 1
            if not chunk:
                raise _error("authenticated numeric crop stream ended before its denominator")
            offset = 0
            while offset < len(chunk):
                raw_batch = chunk[offset : offset + batch_size]
                metadata, images = _samples(
                    raw_batch,
                    first_ordinal=first_sample_ordinal + cursor + offset,
                    archive_axis=True,
                )
                results = recognizer.predict(input=images, batch_size=batch_size)
                counts["recognizer_predict_call_count"] += 1
                if type(results) is not list or len(results) != len(metadata):
                    raise _error("PP-OCRv6 numeric recognizer changed a streamed crop denominator")
                for sample, result in zip(metadata, results, strict=True):
                    raw_text, score = _provider_result(result)
                    result_sink(
                        {
                            "crop_sha256": sample["crop_sha256"],
                            "raw_prediction": raw_text,
                            "reader_score": score,
                            "sample_id": sample["sample_id"],
                        }
                    )
                    counts["result_count"] += 1
                offset += len(raw_batch)
            cursor += len(chunk)
        if require_archive_end:
            trailing = read_authenticated_family_first_semantic_label_chunk_v1(
                reader_session, maximum_samples=1
            )
            counts["reader_chunk_call_count"] += 1
            if trailing:
                raise _error("authenticated numeric crop stream retained trailing samples")
        if cursor != expected_sample_count or counts["result_count"] != expected_sample_count:
            raise _error("PP-OCRv6 numeric execution denominator drifted")
        after, _directory = _recognizer_projection(project_root, model_cache)
        if after != before:
            raise _error("PP-OCRv6 numeric model changed during inference")
        runtime = {
            "device": "cpu",
            "model": before,
            "packages": {
                "paddleocr": importlib.metadata.version("paddleocr"),
                "paddlepaddle": importlib.metadata.version("paddlepaddle"),
            },
            "precision": "fp32",
        }
        metrics = {
            "model_load_seconds": float(model_load_seconds),
            "total_wall_seconds": float(time.perf_counter() - started),
        }
        return runtime, counts, metrics
    finally:
        shutil.rmtree(snapshot)
