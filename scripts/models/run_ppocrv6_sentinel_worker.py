from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SENTINEL_RUNTIME_ROOT = (
    PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1/runtime"
)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bctc_ai.corpus.wave1_role_b_word_box_normalization import (  # noqa: E402
    normalize_ppocrv6_word_boxes,
    validate_normalization_authority,
)
from bctc_ai.ocr.ppocrv6_page_session import PPOCRV6PageSession, _plain_json  # noqa: E402


class SentinelWorkerError(RuntimeError):
    """The isolated pinned worker cannot produce an authenticated response."""


_SHA256_CHARACTERS = frozenset("0123456789abcdef")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_CHARACTERS


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _open_absolute_directory(path: Path) -> tuple[list[int], int]:
    if not path.is_absolute() or ".." in PurePosixPath(path.as_posix()).parts:
        raise SentinelWorkerError("worker directory path is not canonical absolute")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors = [os.open("/", flags)]
    try:
        for part in path.parts[1:]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        return descriptors, descriptors[-1]
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _read_absolute_file(path: Path) -> bytes:
    descriptors, directory_fd = _open_absolute_directory(path.parent)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path.name, flags, dir_fd=directory_fd)
        try:
            before = os.fstat(descriptor)
            named_before = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise SentinelWorkerError("worker input is not a regular file")
            chunks = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            payload = b"".join(chunks)
            after = os.fstat(descriptor)
            named_after = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            if (
                identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (named_before.st_dev, named_before.st_ino, named_before.st_size)
                != (before.st_dev, before.st_ino, before.st_size)
                or (named_after.st_dev, named_after.st_ino, named_after.st_size)
                != (after.st_dev, after.st_ino, after.st_size)
            ):
                raise SentinelWorkerError("worker input changed while being read")
            return payload
        finally:
            os.close(descriptor)
    finally:
        for parent in reversed(descriptors):
            os.close(parent)


def _image_identity(identity: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        identity.st_dev,
        identity.st_ino,
        identity.st_size,
        identity.st_mtime_ns,
        identity.st_ctime_ns,
    )


def _hash_fd(descriptor: int) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    hasher = hashlib.sha256()
    while chunk := os.read(descriptor, 1024 * 1024):
        hasher.update(chunk)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return hasher.hexdigest()


def _open_image_fd(
    path: Path,
    expected_sha256: str,
    expected_size: int,
) -> tuple[int, tuple[int, int, int, int, int]]:
    if not path.is_absolute() or path.suffix != ".png":
        raise SentinelWorkerError("worker render path is not an absolute PNG name")
    descriptors, directory_fd = _open_absolute_directory(path.parent)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path.name, flags, dir_fd=directory_fd)
        before = os.fstat(descriptor)
        named_before = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o444
            or before.st_nlink != 1
            or (before.st_dev, before.st_ino, before.st_size)
            != (named_before.st_dev, named_before.st_ino, named_before.st_size)
            or before.st_size != expected_size
        ):
            os.close(descriptor)
            raise SentinelWorkerError("worker render file identity drifted")
        observed_sha256 = _hash_fd(descriptor)
        after = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            observed_sha256 != expected_sha256
            or _image_identity(after) != _image_identity(before)
            or (named_after.st_dev, named_after.st_ino, named_after.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            os.close(descriptor)
            raise SentinelWorkerError("worker render hash drifted")
        return descriptor, _image_identity(after)
    finally:
        for parent in reversed(descriptors):
            os.close(parent)


def _publish_response(directory_fd: int, filename: str, payload: bytes) -> None:
    temporary = f".{filename}.{secrets.token_hex(16)}.tmp"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
    owned = os.fstat(descriptor)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        try:
            os.link(
                temporary,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise SentinelWorkerError("worker response already exists") from error
        os.fsync(directory_fd)
        final_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        final_fd = os.open(filename, final_flags, dir_fd=directory_fd)
        try:
            final = os.fstat(final_fd)
            named = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
            observed = b""
            while chunk := os.read(final_fd, 1024 * 1024):
                observed += chunk
            if (
                observed != payload
                or stat.S_IMODE(final.st_mode) != 0o444
                or (final.st_dev, final.st_ino, final.st_size)
                != (owned.st_dev, owned.st_ino, len(payload))
                or (named.st_dev, named.st_ino, named.st_size)
                != (final.st_dev, final.st_ino, final.st_size)
            ):
                raise SentinelWorkerError("worker response publication drifted")
        finally:
            os.close(final_fd)
    finally:
        os.close(descriptor)
        try:
            temporary_identity = os.stat(temporary, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            temporary_identity = None
        if temporary_identity is not None and (
            temporary_identity.st_dev,
            temporary_identity.st_ino,
        ) == (owned.st_dev, owned.st_ino):
            os.unlink(temporary, dir_fd=directory_fd)
            os.fsync(directory_fd)


def _validate_file_identity(path: Path, identity: dict[str, Any], label: str) -> None:
    if not isinstance(identity, dict) or set(identity) != {"path", "sha256", "size_bytes"}:
        raise SentinelWorkerError(f"{label} identity fields drifted")
    if identity["path"] != path.as_posix() or not _is_sha256(identity["sha256"]):
        raise SentinelWorkerError(f"{label} locator or digest drifted")
    payload = _read_absolute_file(path)
    if (
        isinstance(identity["size_bytes"], bool)
        or not isinstance(identity["size_bytes"], int)
        or len(payload) != identity["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != identity["sha256"]
    ):
        raise SentinelWorkerError(f"{label} bytes drifted")


def _actual_model_inventory(directory: Path) -> tuple[dict[str, tuple[str, int]], set[str]]:
    descriptors, root_fd = _open_absolute_directory(directory)
    files: dict[str, tuple[str, int]] = {}
    directories: set[str] = set()

    def visit(directory_fd: int, prefix: PurePosixPath) -> None:
        for name in sorted(os.listdir(directory_fd)):
            if not name or "/" in name or name in {".", ".."}:
                raise SentinelWorkerError("model inventory contains an invalid name")
            identity = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            relative = prefix / name
            if stat.S_ISLNK(identity.st_mode):
                raise SentinelWorkerError("model inventory contains a symlink")
            if stat.S_ISDIR(identity.st_mode):
                directories.add(relative.as_posix())
                flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
                child_fd = os.open(name, flags, dir_fd=directory_fd)
                try:
                    child = os.fstat(child_fd)
                    if (child.st_dev, child.st_ino) != (identity.st_dev, identity.st_ino):
                        raise SentinelWorkerError("model directory name changed during inventory")
                    visit(child_fd, relative)
                    named_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if (named_after.st_dev, named_after.st_ino) != (child.st_dev, child.st_ino):
                        raise SentinelWorkerError("model directory changed during inventory")
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(identity.st_mode):
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                file_fd = os.open(name, flags, dir_fd=directory_fd)
                try:
                    opened = os.fstat(file_fd)
                    hasher = hashlib.sha256()
                    while block := os.read(file_fd, 1024 * 1024):
                        hasher.update(block)
                    named_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if (opened.st_dev, opened.st_ino, opened.st_size) != (
                        identity.st_dev,
                        identity.st_ino,
                        identity.st_size,
                    ) or (named_after.st_dev, named_after.st_ino, named_after.st_size) != (
                        opened.st_dev,
                        opened.st_ino,
                        opened.st_size,
                    ):
                        raise SentinelWorkerError("model file changed during inventory")
                    files[relative.as_posix()] = (hasher.hexdigest(), opened.st_size)
                finally:
                    os.close(file_fd)
            else:
                raise SentinelWorkerError("model inventory contains a non-regular entry")

    try:
        visit(root_fd, PurePosixPath())
        return files, directories
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _validate_model_inventory(model: dict[str, Any]) -> None:
    if not isinstance(model, dict) or set(model) != {"key", "directory", "files"}:
        raise SentinelWorkerError("worker model inventory fields drifted")
    directory = Path(model["directory"])
    if not directory.is_absolute() or not isinstance(model["files"], list) or not model["files"]:
        raise SentinelWorkerError("worker model inventory is malformed")
    expected_files: dict[str, tuple[str, int]] = {}
    expected_directories: set[str] = set()
    for record in model["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size_bytes"}:
            raise SentinelWorkerError("worker model file fields drifted")
        relative = PurePosixPath(record["path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() in expected_files
            or not _is_sha256(record["sha256"])
            or isinstance(record["size_bytes"], bool)
            or not isinstance(record["size_bytes"], int)
            or record["size_bytes"] < 0
        ):
            raise SentinelWorkerError("worker model file path is invalid")
        expected_files[relative.as_posix()] = (record["sha256"], record["size_bytes"])
        for parent in relative.parents:
            if parent != PurePosixPath("."):
                expected_directories.add(parent.as_posix())
    actual_files, actual_directories = _actual_model_inventory(directory)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise SentinelWorkerError(f"full model inventory drifted: {model['key']}")


def _validate_execution_lease(lease: dict[str, Any]) -> None:
    if not isinstance(lease, dict) or set(lease) != {"fd", "device", "inode"}:
        raise SentinelWorkerError("inherited execution lease fields drifted")
    if any(
        isinstance(lease[key], bool) or not isinstance(lease[key], int) or lease[key] < 0
        for key in ("fd", "device", "inode")
    ):
        raise SentinelWorkerError("inherited execution lease identity is malformed")
    try:
        identity = os.fstat(lease["fd"])
    except OSError as error:
        raise SentinelWorkerError("inherited execution lease descriptor is absent") from error
    if (
        not stat.S_ISREG(identity.st_mode)
        or stat.S_IMODE(identity.st_mode) != 0o600
        or identity.st_nlink != 1
        or identity.st_size != 0
        or (identity.st_dev, identity.st_ino) != (lease["device"], lease["inode"])
    ):
        raise SentinelWorkerError("inherited execution lease identity drifted")


def _predict_from_held_render(
    session: PPOCRV6PageSession,
    image_fd: int,
    image_path: Path,
    *,
    pixel_width: int,
    pixel_height: int,
    normalization_authority: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Call the provider with a held, suffix-bearing private lexical PNG path."""

    pipeline = session._pipeline  # noqa: SLF001 - sealed B adapter to immutable A session
    if pipeline is None or image_fd < 0:
        raise SentinelWorkerError("PP-OCR session is not loaded")
    if not image_path.is_absolute() or image_path.suffix != ".png":
        raise SentinelWorkerError("PP-OCR provider input is not an absolute PNG path")
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
        raise SentinelWorkerError("PP-OCR provider did not return exactly one page")
    payload = _plain_json(results[0].json["res"])
    if not isinstance(payload, dict):
        raise SentinelWorkerError("PP-OCR provider response is not an object")
    _normalized, normalization_ledger = normalize_ppocrv6_word_boxes(
        payload,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        authority=normalization_authority,
    )
    return payload, normalization_ledger, elapsed


def _revalidate_held_render(
    image_fd: int,
    image_path: Path,
    original_identity: tuple[int, int, int, int, int],
    *,
    expected_sha256: str,
    expected_size: int,
) -> None:
    if not image_path.is_absolute() or image_path.suffix != ".png":
        raise SentinelWorkerError("held render lexical path drifted during inference")
    held_before = os.fstat(image_fd)
    descriptors, directory_fd = _open_absolute_directory(image_path.parent)
    named_fd = -1
    try:
        named_fd = os.open(
            image_path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        named_before = os.stat(
            image_path.name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        reopened_before = os.fstat(named_fd)
        held_sha256 = _hash_fd(image_fd)
        named_sha256 = _hash_fd(named_fd)
        held_after = os.fstat(image_fd)
        reopened_after = os.fstat(named_fd)
        named_after = os.stat(
            image_path.name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            _image_identity(held_before) != original_identity
            or _image_identity(held_after) != original_identity
            or _image_identity(reopened_before) != original_identity
            or _image_identity(reopened_after) != original_identity
            or _image_identity(named_before) != original_identity
            or _image_identity(named_after) != original_identity
            or not stat.S_ISREG(held_after.st_mode)
            or stat.S_IMODE(held_after.st_mode) != 0o444
            or held_after.st_nlink != 1
            or stat.S_IMODE(reopened_after.st_mode) != 0o444
            or reopened_after.st_nlink != 1
            or held_after.st_size != expected_size
            or held_sha256 != expected_sha256
            or named_sha256 != expected_sha256
        ):
            raise SentinelWorkerError("held render identity drifted during inference")
    finally:
        if named_fd >= 0:
            os.close(named_fd)
        for parent in reversed(descriptors):
            os.close(parent)


def _expected_shard_runtime_root(execution_nonce: str, shard_id: int) -> Path:
    if not _is_sha256(execution_nonce) or isinstance(shard_id, bool) or shard_id not in {0, 1}:
        raise SentinelWorkerError("worker runtime identity is malformed")
    return SENTINEL_RUNTIME_ROOT / f"execution-{execution_nonce}" / f"shard-{shard_id}"


def _validate_private_input_path(
    task_path: Path,
    execution_nonce: str,
    shard_id: int,
    request_sha256: str,
    image_path: str,
) -> Path:
    expected_shard = _expected_shard_runtime_root(execution_nonce, shard_id)
    expected_task = expected_shard / "task.json"
    expected_image = expected_shard / "inputs" / f"{request_sha256}.png"
    if task_path.as_posix() != expected_task.as_posix() or image_path != expected_image.as_posix():
        raise SentinelWorkerError("private provider input runtime binding drifted")
    return expected_image


def _load_task(path: Path) -> dict[str, Any]:
    payload = _read_absolute_file(path)
    try:
        task = json.loads(payload)
    except json.JSONDecodeError as error:
        raise SentinelWorkerError("worker task is invalid JSON") from error
    if not isinstance(task, dict) or _canonical_bytes(task) != payload:
        raise SentinelWorkerError("worker task is not canonical JSON")
    if set(task) != {
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
        "requests",
    }:
        raise SentinelWorkerError("worker task fields drifted")
    if (
        task["format_version"] != "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_TASK_V2"
        or task["protocol"] != "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_V1"
        or isinstance(task["shard_id"], bool)
        or not isinstance(task["shard_id"], int)
        or task["shard_id"] not in {0, 1}
        or not _is_sha256(task["provider_identity_sha256"])
        or task["cpu_threads"] != 6
        or not isinstance(task["execution_nonce"], str)
        or len(task["execution_nonce"]) != 64
        or not isinstance(task["expected_environment"], dict)
        or os.environ != task["expected_environment"]
        or not isinstance(task["models"], list)
        or len(task["models"]) != 2
        or not isinstance(task["requests"], list)
        or not task["requests"]
    ):
        raise SentinelWorkerError("worker task contract or scrubbed environment drifted")
    try:
        validate_normalization_authority(task["word_box_normalization_authority"])
    except RuntimeError as error:
        raise SentinelWorkerError("worker normalization authority drifted") from error
    configuration = task["configuration"]
    if not isinstance(configuration, dict) or set(configuration) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise SentinelWorkerError("worker configuration identity drifted")
    _validate_file_identity(Path(configuration["path"]), configuration, "PP-OCR configuration")
    _validate_execution_lease(task["execution_lease"])
    for model in task["models"]:
        _validate_model_inventory(model)
    seen = set()
    for request in task["requests"]:
        if not isinstance(request, dict) or set(request) != {
            "request_sha256",
            "render_sha256",
            "render_size_bytes",
            "image_path",
            "pixel_width",
            "pixel_height",
            "response_filename",
        }:
            raise SentinelWorkerError("worker page task fields drifted")
        image_path = request.get("image_path")
        request_sha256 = request.get("request_sha256")
        if (
            not _is_sha256(request_sha256)
            or not _is_sha256(request["render_sha256"])
            or request_sha256 in seen
            or request["response_filename"] != f"{request_sha256}.response.json"
            or not isinstance(image_path, str)
            or not Path(image_path).is_absolute()
            or PurePosixPath(image_path).as_posix() != image_path
            or ".." in PurePosixPath(image_path).parts
            or Path(image_path).name != f"{request_sha256}.png"
            or isinstance(request["render_size_bytes"], bool)
            or not isinstance(request["render_size_bytes"], int)
            or request["render_size_bytes"] <= 0
            or any(
                isinstance(request[key], bool)
                or not isinstance(request[key], int)
                or request[key] <= 0
                for key in ("pixel_width", "pixel_height")
            )
        ):
            raise SentinelWorkerError("worker page task identity drifted")
        _validate_private_input_path(
            path,
            task["execution_nonce"],
            task["shard_id"],
            request_sha256,
            image_path,
        )
        seen.add(request_sha256)
    return task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one authenticated PP-OCR sentinel shard")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--response-directory", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    task = _load_task(arguments.task)
    expected_response_directory = (
        _expected_shard_runtime_root(
            task["execution_nonce"],
            task["shard_id"],
        )
        / "responses"
    )
    if arguments.response_directory.as_posix() != expected_response_directory.as_posix():
        raise SentinelWorkerError("worker response runtime binding drifted")
    _validate_execution_lease(task["execution_lease"])
    os.set_inheritable(task["execution_lease"]["fd"], False)
    response_descriptors, response_fd = _open_absolute_directory(arguments.response_directory)
    configuration = Path(task["configuration"]["path"])
    models = {model["key"]: model for model in task["models"]}
    if set(models) != {"pp_ocrv6_medium_det", "pp_ocrv6_medium_rec"}:
        raise SentinelWorkerError("worker model keys drifted")
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
                    payload, normalization_ledger, elapsed = _predict_from_held_render(
                        session,
                        image_fd,
                        image_path,
                        pixel_width=request["pixel_width"],
                        pixel_height=request["pixel_height"],
                        normalization_authority=task["word_box_normalization_authority"],
                    )
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
                    configuration,
                    task["configuration"],
                    "PP-OCR configuration",
                )
                for model in task["models"]:
                    _validate_model_inventory(model)
                _validate_execution_lease(task["execution_lease"])
                response = {
                    "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_RESPONSE_V2",
                    "execution_nonce": task["execution_nonce"],
                    "shard_id": task["shard_id"],
                    "request_sha256": request["request_sha256"],
                    "render_sha256": request["render_sha256"],
                    "provider_identity_sha256": task["provider_identity_sha256"],
                    "payload": payload,
                    "word_box_normalization_ledger": normalization_ledger,
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
        for descriptor in reversed(response_descriptors):
            os.close(descriptor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
