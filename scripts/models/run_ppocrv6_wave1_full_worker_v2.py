from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FULL_RUNTIME_ROOT = (
    PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v2/runtime"
)
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from bctc_ai.corpus.wave1_role_b_word_box_normalization import (  # noqa: E402
    WaveOneRoleBWordBoxNormalizationError,
    normalize_ppocrv6_word_boxes,
    validate_normalization_authority,
)
from bctc_ai.ocr.ppocrv6_page_session import PPOCRV6PageSession  # noqa: E402
from scripts.models.run_ppocrv6_sentinel_worker import (  # noqa: E402
    _canonical_bytes,
    _is_sha256,
    _open_absolute_directory,
    _open_image_fd,
    _plain_json,
    _publish_response,
    _read_absolute_file,
    _revalidate_held_render,
    _validate_execution_lease,
    _validate_file_identity,
    _validate_model_inventory,
)


class FullReaderWorkerError(RuntimeError):
    """One isolated full-reader PP-OCR batch violated its fixed protocol."""


def _expected_shard_root(execution_nonce: str, shard_id: int) -> Path:
    if not _is_sha256(execution_nonce) or isinstance(shard_id, bool) or shard_id not in {0, 1}:
        raise FullReaderWorkerError("full worker runtime identity is malformed")
    return FULL_RUNTIME_ROOT / f"execution-{execution_nonce}" / f"shard-{shard_id}"


def _load_task(path: Path) -> dict[str, Any]:
    payload = _read_absolute_file(path)
    try:
        task = json.loads(payload)
    except json.JSONDecodeError as error:
        raise FullReaderWorkerError("full worker task is invalid JSON") from error
    required = {
        "format_version",
        "protocol",
        "execution_nonce",
        "shard_id",
        "provider_identity_sha256",
        "word_box_normalization_authority",
        "cpu_threads",
        "expected_environment",
        "execution_lease",
        "configuration",
        "models",
        "max_request_count",
        "requests",
    }
    if not isinstance(task, dict) or _canonical_bytes(task) != payload or set(task) != required:
        raise FullReaderWorkerError("full worker task fields drifted")
    if (
        task["format_version"] != "BANK_CORPUS_WAVE_1_PPOCRV6_FULL_WORKER_TASK_V2"
        or task["protocol"] != "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_WITH_PUBLICATION_STATE_V2"
        or task["shard_id"] not in {0, 1}
        or type(task["shard_id"]) is not int
        or not _is_sha256(task["provider_identity_sha256"])
        or type(task["cpu_threads"]) is not int
        or task["cpu_threads"] != 6
        or type(task["max_request_count"]) is not int
        or task["max_request_count"] != 128
        or not isinstance(task["expected_environment"], dict)
        or os.environ != task["expected_environment"]
        or not isinstance(task["models"], list)
        or len(task["models"]) != 2
        or not isinstance(task["requests"], list)
        or not 1 <= len(task["requests"]) <= 128
    ):
        raise FullReaderWorkerError("full worker task contract drifted")
    expected_shard = _expected_shard_root(task["execution_nonce"], task["shard_id"])
    if path.as_posix() != (expected_shard / "task.json").as_posix():
        raise FullReaderWorkerError("full worker task runtime binding drifted")
    try:
        validate_normalization_authority(task["word_box_normalization_authority"])
        _validate_execution_lease(task["execution_lease"])
    except RuntimeError as error:
        raise FullReaderWorkerError("full worker authority drifted") from error
    configuration = task["configuration"]
    if not isinstance(configuration, dict) or set(configuration) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise FullReaderWorkerError("full worker configuration fields drifted")
    _validate_file_identity(Path(configuration["path"]), configuration, "PP-OCR configuration")
    for model in task["models"]:
        _validate_model_inventory(model)
    seen = set()
    for request in task["requests"]:
        required_request = {
            "request_sha256",
            "render_sha256",
            "render_size_bytes",
            "image_path",
            "pixel_width",
            "pixel_height",
            "response_filename",
        }
        if not isinstance(request, dict) or set(request) != required_request:
            raise FullReaderWorkerError("full worker page fields drifted")
        request_sha = request["request_sha256"]
        expected_image = expected_shard / "inputs" / f"{request_sha}.png"
        image_path = request["image_path"]
        if (
            not _is_sha256(request_sha)
            or request_sha in seen
            or not _is_sha256(request["render_sha256"])
            or request["response_filename"] != f"{request_sha}.response.json"
            or not isinstance(image_path, str)
            or PurePosixPath(image_path).as_posix() != image_path
            or image_path != expected_image.as_posix()
            or any(
                isinstance(request[key], bool)
                or not isinstance(request[key], int)
                or request[key] <= 0
                for key in ("render_size_bytes", "pixel_width", "pixel_height")
            )
        ):
            raise FullReaderWorkerError("full worker page identity drifted")
        seen.add(request_sha)
    return task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one authenticated Wave-1 PP-OCR batch")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--response-directory", type=Path, required=True)
    return parser.parse_args()


def _predict_provider_raw(
    session: PPOCRV6PageSession, image_path: Path
) -> tuple[dict[str, Any], float]:
    pipeline = session._pipeline  # noqa: SLF001 - fixed adapter to pinned session
    if pipeline is None or not image_path.is_absolute() or image_path.suffix != ".png":
        raise FullReaderWorkerError("full worker PP-OCR provider is not loaded")
    started = time.perf_counter()
    results = pipeline.predict(
        image_path.as_posix(),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        return_word_box=True,
    )
    elapsed = time.perf_counter() - started
    if len(results) != 1:
        raise FullReaderWorkerError("PP-OCR provider did not return exactly one page")
    payload = _plain_json(results[0].json["res"])
    if not isinstance(payload, dict):
        raise FullReaderWorkerError("PP-OCR provider response is not an object")
    return payload, elapsed


def main() -> int:
    arguments = parse_args()
    task = _load_task(arguments.task)
    expected_shard = _expected_shard_root(task["execution_nonce"], task["shard_id"])
    if arguments.response_directory.as_posix() != (expected_shard / "responses").as_posix():
        raise FullReaderWorkerError("full worker response runtime binding drifted")
    _validate_execution_lease(task["execution_lease"])
    os.set_inheritable(task["execution_lease"]["fd"], False)
    descriptors, response_fd = _open_absolute_directory(arguments.response_directory)
    configuration = Path(task["configuration"]["path"])
    models = {model["key"]: model for model in task["models"]}
    if set(models) != {"pp_ocrv6_medium_det", "pp_ocrv6_medium_rec"}:
        raise FullReaderWorkerError("full worker model keys drifted")
    try:
        with PPOCRV6PageSession(
            configuration_path=configuration,
            detection_model_directory=Path(models["pp_ocrv6_medium_det"]["directory"]),
            recognition_model_directory=Path(models["pp_ocrv6_medium_rec"]["directory"]),
            cpu_threads=6,
        ) as session:
            for request in task["requests"]:
                image_path = Path(request["image_path"])
                image_fd, image_identity = _open_image_fd(
                    image_path,
                    request["render_sha256"],
                    request["render_size_bytes"],
                )
                try:
                    payload, elapsed = _predict_provider_raw(session, image_path)
                    try:
                        _normalized, ledger = normalize_ppocrv6_word_boxes(
                            payload,
                            pixel_width=request["pixel_width"],
                            pixel_height=request["pixel_height"],
                            authority=task["word_box_normalization_authority"],
                        )
                    except WaveOneRoleBWordBoxNormalizationError:
                        ledger = None
                    _revalidate_held_render(
                        image_fd,
                        image_path,
                        image_identity,
                        expected_sha256=request["render_sha256"],
                        expected_size=request["render_size_bytes"],
                    )
                finally:
                    os.close(image_fd)
                _validate_file_identity(
                    configuration, task["configuration"], "PP-OCR configuration"
                )
                for model in task["models"]:
                    _validate_model_inventory(model)
                _validate_execution_lease(task["execution_lease"])
                response = {
                    "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_FULL_WORKER_RESPONSE_V2",
                    "execution_nonce": task["execution_nonce"],
                    "shard_id": task["shard_id"],
                    "request_sha256": request["request_sha256"],
                    "render_sha256": request["render_sha256"],
                    "provider_identity_sha256": task["provider_identity_sha256"],
                    "payload": payload,
                    "word_box_normalization_ledger": ledger,
                    "normalization_outcome": (
                        "NORMALIZATION_COMPLETE"
                        if ledger is not None
                        else "BOUNDED_NORMALIZATION_FAILURE_CANDIDATE"
                    ),
                    "observational": {
                        "model_load_wall_seconds": session.model_load_wall_seconds,
                        "inference_wall_seconds": elapsed,
                    },
                }
                _publish_response(
                    response_fd,
                    request["response_filename"],
                    _canonical_bytes(response),
                )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
