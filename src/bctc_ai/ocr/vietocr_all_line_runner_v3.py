"""One fresh, reference-blind VietOCR Transformer run over the V3 freeze.

The runner consumes only an opaque live freezer capability.  Crop pixels enter
the model from one immutable in-memory batch; reader-visible filesystem paths,
bank identities, source transcripts, schema metadata, and prior outputs never
enter the inference boundary.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from bctc_ai.evaluation.vietocr_all_line_freezer_v3 import (
    EXPECTED_LINE_COUNT_VECTOR,
    EXPECTED_SAMPLE_COUNT,
    AuthenticatedVietOCRAllLineFreezeV3,
    assert_authenticated_vietocr_all_line_freeze_project_root_v3,
    read_authenticated_vietocr_all_line_snapshot_v3,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "CONFIG_PATH",
    "RUN_ROOT",
    "VietOCRAllLineRunnerV3Error",
    "run_authenticated_vietocr_all_line_v3",
]


class VietOCRAllLineRunnerV3Error(RuntimeError):
    """The single formal V3 inference attempt cannot be established."""


CONFIG_PATH = Path("config/models/vietocr-0.3.13-vgg-transformer-all-line-v3.toml")
RUN_ROOT = Path("output/development/vietocr-all-line-vgg-transformer-v3/fresh-run")
RUNTIME_ROOT = Path("/workspace/bctc-ai-runtime/vietocr-0.3.13")
EXPERIMENT_ID = "VIETOCR_VGG_TRANSFORMER_ALL_LINE_8X835_V3"
RESULT_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_RESULT_V3"
RUN_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_RUN_MANIFEST_V3"
ATTEMPT_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_ATTEMPT_V3"
_IMPLEMENTATION_PATH = Path("src/bctc_ai/ocr/vietocr_all_line_runner_v3.py")
_FREEZER_PATH = Path("src/bctc_ai/evaluation/vietocr_all_line_freezer_v3.py")
_ORCHESTRATOR_PATH = Path("scripts/experiments/run_vietocr_all_line_8bank_v3.py")
_ATTEMPT_NAME = "attempt.json"
_RESULT_NAME = "ocr_result.json"
_RUN_NAME = "run_manifest.json"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

_INFERENCE_POLICY = {
    "beam_search": False,
    "cnn_pretrained_download": False,
    "device": "cuda:0",
    "input_color_mode": "RGB",
    "max_sequence_length": 128,
    "network_permitted": False,
    "random_seed": 20260807,
    "reference_text_available_to_decoder": False,
    "upstream_image_height": 32,
    "upstream_image_max_width": 512,
    "upstream_image_min_width": 32,
}

_EXPECTED_PACKAGES = {
    "einops": "0.8.2",
    "numpy": "2.3.5",
    "pillow": "12.3.0",
    "pyyaml": "6.0.2",
    "torch": "2.12.0+cu130",
    "torchvision": "0.27.0+cu130",
    "vietocr": "0.3.13",
}
_EXPECTED_ARTIFACTS = {
    "base_config": ("9c8283fadb950f06f5d3400475f80d5355700ff315c9c48b7875e6ea66647d1c", 1809),
    "model_config": ("0df9feee197754c7381871e5dfd07c6f3e292a4853eece6f1af240923e57c907", 505),
    "weights": ("380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59", 151815373),
    "wheel": ("07b3777e5176b0d733cb056b68bd817371605f4b3514795fbf91ad4e181b8ccf", 34641),
}
_EXECUTION_POLICY = {
    "amp": False,
    "autocast": False,
    "backend": "PYTORCH_EAGER",
    "beam_search": False,
    "bf16": False,
    "cnn_pretrained_download": False,
    "fp16": False,
    "history_access": False,
    "human_review_access": False,
    "network_permitted": False,
    "onnx": False,
    "post_correction": False,
    "precision": "FP32",
    "prior_outputs": False,
    "reference_text_available_to_decoder": False,
    "resume": False,
    "retry_from_output": False,
    "tf32": False,
    "template_access": False,
    "torch_compile": False,
    "torchscript": False,
    "truth_access": False,
}
_SAFETY = {
    "accounting_authority": False,
    "automatic_post_correction": False,
    "automatic_truth_promotion": False,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "period_authority": False,
    "report_norm_id_authority": False,
    "schema_authority": False,
    "scope_authority": False,
    "semantic_acceptance": False,
    "sign_authority": False,
    "unit_authority": False,
}


def _error(message: str) -> VietOCRAllLineRunnerV3Error:
    return VietOCRAllLineRunnerV3Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _resolve_root(value: Path) -> Path:
    if not isinstance(value, Path):
        raise _error("project root must be a pathlib Path")
    root = value.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise _error("project root is not a safe real directory")
    try:
        top_level_text = _git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise _error("Git top-level path is not UTF-8") from exc
    top_level_path = Path(top_level_text)
    if not top_level_text or not top_level_path.is_absolute():
        raise _error("Git top-level path is malformed")
    try:
        top_level = top_level_path.resolve(strict=True)
    except OSError as exc:
        raise _error("Git top-level path cannot be resolved") from exc
    if top_level != root:
        raise _error("project root must exactly equal the Git top-level directory")
    return root


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as exc:
        raise _error(f"Git provenance check failed: {' '.join(args)}") from exc


def _stable_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink():
        raise _error(f"{label} cannot be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise _error(f"cannot open {label}") from exc
    try:
        before = os.fstat(descriptor)
        if not os.path.isfile(f"/proc/self/fd/{descriptor}"):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise _error(f"{label} changed during its authenticated read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_fd_bytes(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise _error(f"formal output changed during readback: {name}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _tracked_ref(root: Path, relative: Path, label: str) -> dict[str, Any]:
    path = root / relative
    payload = _stable_bytes(path, label)
    committed = _git(root, "show", f"HEAD:{relative.as_posix()}")
    if payload != committed:
        raise _error(f"{label} differs from its clean HEAD blob")
    return {"path": relative.as_posix(), "sha256": _sha(payload), "size_bytes": len(payload)}


def _git_binding(root: Path) -> dict[str, Any]:
    status = _git(root, "status", "--porcelain", "--untracked-files=normal")
    if status:
        raise _error("formal V3 inference requires a clean Git worktree")
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    tree = _git(root, "rev-parse", "HEAD:src/bctc_ai").decode().strip()
    if _COMMIT_RE.fullmatch(commit) is None or _COMMIT_RE.fullmatch(tree) is None:
        raise _error("formal V3 Git identity is malformed")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_refs": [
            _tracked_ref(root, _FREEZER_PATH, "V3 freezer implementation"),
            _tracked_ref(root, _IMPLEMENTATION_PATH, "V3 runner implementation"),
            _tracked_ref(root, _ORCHESTRATOR_PATH, "V3 run orchestrator"),
            _tracked_ref(root, CONFIG_PATH, "V3 runner configuration"),
        ],
        "source_tree_oid": tree,
    }


def _validate_config(payload: bytes) -> dict[str, Any]:
    try:
        value = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _error("V3 VietOCR configuration cannot be decoded") from exc
    required = {
        "architecture",
        "artifacts",
        "backbone",
        "execution_engine",
        "execution_policy",
        "format_version",
        "inference",
        "license",
        "metadata_license_note",
        "model_name",
        "package_version",
        "precision",
        "runtime",
        "runtime_compatibility",
        "safety",
        "sequence_modeling",
        "status",
        "version",
    }
    if set(value) != required:
        raise _error("V3 VietOCR configuration fields drifted")
    inference = value["inference"]
    compatibility = value["runtime_compatibility"]
    runtime = value["runtime"]
    execution_policy = value["execution_policy"]
    safety = value["safety"]
    if (
        type(execution_policy) is not dict
        or any(type(item) is not bool for item in execution_policy.values())
        or type(safety) is not dict
        or any(type(item) is not bool for item in safety.values())
    ):
        raise _error("V3 VietOCR model, execution, runtime, or safety policy drifted")
    if (
        type(value["version"]) is not int
        or value["version"] != 3
        or value["format_version"] != "BCTC_AI_VIETOCR_VGG_TRANSFORMER_ALL_LINE_CONFIG_V3"
        or value["status"] != "FRESH_SINGLE_RUN_REFERENCE_BLIND_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or value["model_name"] != "VietOCR VGG Transformer"
        or value["package_version"] != "0.3.13"
        or value["architecture"] != "vgg19_bn_transformer"
        or value["backbone"] != "vgg19_bn"
        or value["sequence_modeling"] != "transformer"
        or value["execution_engine"] != "PYTORCH_EAGER"
        or value["precision"] != "FP32"
        or value["license"] != "Apache-2.0 as shipped in wheel LICENSE"
        or value["metadata_license_note"]
        != "PyPI classifier says MIT while wheel LICENSE and project description say Apache-2.0"
        or type(inference) is not dict
        or not same_typed_json_v1(inference, _INFERENCE_POLICY)
        or execution_policy
        != {
            "amp": False,
            "autocast": False,
            "bf16": False,
            "fp16": False,
            "history_access": False,
            "human_review_access": False,
            "onnx": False,
            "post_correction": False,
            "prior_outputs": False,
            "resume": False,
            "retry_from_output": False,
            "template_access": False,
            "tf32": False,
            "torch_compile": False,
            "torchscript": False,
            "truth_access": False,
        }
        or type(runtime) is not dict
        or set(runtime) != {"packages", "python_major_minor", "site_packages"}
        or not same_typed_json_v1(runtime["packages"], _EXPECTED_PACKAGES)
        or runtime["python_major_minor"] != "3.11"
        or runtime["site_packages"] != "site-packages"
        or not same_typed_json_v1(
            compatibility,
            {
                "compute_capability": [8, 9],
                "cuda_runtime": "13.0",
                "device_name": "NVIDIA GeForce RTX 4090",
                "gpu_family": "NVIDIA_GEFORCE_RTX_4090_ADA",
            },
        )
        or safety
        != {
            "accounting_authority": False,
            "automatic_post_correction": False,
            "automatic_truth_promotion": False,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "period_authority": False,
            "report_norm_id_authority": False,
            "schema_authority": False,
            "scope_authority": False,
            "semantic_acceptance": False,
            "sign_authority": False,
            "unit_authority": False,
        }
    ):
        raise _error("V3 VietOCR model, execution, runtime, or safety policy drifted")
    if set(value["artifacts"]) != set(_EXPECTED_ARTIFACTS):
        raise _error("V3 VietOCR artifact registry drifted")
    for name, (expected_sha, expected_size) in _EXPECTED_ARTIFACTS.items():
        record = value["artifacts"][name]
        if (
            type(record) is not dict
            or set(record) != {"path", "sha256", "size_bytes", "url"}
            or record["sha256"] != expected_sha
            or type(record["size_bytes"]) is not int
            or record["size_bytes"] != expected_size
            or type(record["path"]) is not str
            or record["path"]
            != {
                "base_config": "artifacts/base.yml",
                "model_config": "artifacts/vgg-transformer.yml",
                "weights": "artifacts/vgg_transformer.pth",
                "wheel": "artifacts/vietocr-0.3.13-py3-none-any.whl",
            }[name]
            or type(record["url"]) is not str
            or not record["url"].startswith("https://")
        ):
            raise _error(f"V3 VietOCR artifact identity drifted: {name}")
    return value


def _snapshot_runtime(config: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    root = RUNTIME_ROOT.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise _error("fixed VietOCR runtime root is unsafe")
    snapshots: dict[str, bytes] = {}
    records: dict[str, Any] = {}
    for name in sorted(_EXPECTED_ARTIFACTS):
        record = config["artifacts"][name]
        path = (root / record["path"]).resolve(strict=True)
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise _error(f"VietOCR runtime artifact escapes fixed root: {name}") from exc
        payload = _stable_bytes(path, f"VietOCR runtime artifact {name}")
        if len(payload) != record["size_bytes"] or _sha(payload) != record["sha256"]:
            raise _error(f"VietOCR runtime artifact bytes drifted: {name}")
        snapshots[name] = payload
        records[name] = {
            "path": relative.as_posix(),
            "sha256": record["sha256"],
            "size_bytes": record["size_bytes"],
        }
    return snapshots, records


def _verify_wheel_overlay(wheel_bytes: bytes, site_packages: Path) -> None:
    if not site_packages.is_dir() or site_packages.is_symlink():
        raise _error("fixed VietOCR wheel overlay is unavailable")
    try:
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            for member in members:
                installed = site_packages / member.filename
                if _sha(_stable_bytes(installed, f"VietOCR overlay {member.filename}")) != _sha(
                    archive.read(member)
                ):
                    raise _error(f"VietOCR wheel overlay drifted: {member.filename}")
    except zipfile.BadZipFile as exc:
        raise _error("VietOCR wheel snapshot is invalid") from exc


def _materialize_private_wheel_overlay(wheel_bytes: bytes, parent: Path) -> Path:
    """Extract only authenticated wheel members into one private 0700 directory."""

    parent = parent.resolve(strict=True)
    if not parent.is_dir() or parent.is_symlink():
        raise _error("private wheel overlay parent is unsafe")
    overlay = parent / f".vietocr-wheel-v3-{secrets.token_hex(16)}"
    overlay.mkdir(mode=0o700)
    try:
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                relative = Path(member.filename)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or any(not part for part in relative.parts)
                ):
                    raise _error("VietOCR wheel contains an unsafe member path")
                destination = overlay / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                payload = archive.read(member)
                descriptor = os.open(
                    destination,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o400,
                )
                try:
                    view = memoryview(payload)
                    offset = 0
                    while offset < len(view):
                        written = os.write(descriptor, view[offset:])
                        if written <= 0:
                            raise _error("short private VietOCR wheel member write")
                        offset += written
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        return overlay
    except BaseException:
        shutil.rmtree(overlay)
        raise


def _collect_freeze(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if type(capability) is not AuthenticatedVietOCRAllLineFreezeV3:
        raise _error("runner requires the exact live authenticated V3 freeze capability")
    projection, batch = read_authenticated_vietocr_all_line_snapshot_v3(capability)
    if (
        projection.get("sample_count") != EXPECTED_SAMPLE_COUNT
        or projection.get("page_count") != 8
        or projection.get("line_count_vector") != list(EXPECTED_LINE_COUNT_VECTOR)
        or projection.get("state") != "FROZEN_READY_NO_MODEL_RUN"
        or type(batch) is not tuple
        or len(batch) != EXPECTED_SAMPLE_COUNT
    ):
        raise _error("authenticated V3 freeze denominator drifted")
    counts = [0] * 8
    for ordinal, sample in enumerate(batch, start=1):
        if type(sample) is not dict or set(sample) != {
            "crop_png_bytes",
            "crop_sha256",
            "page_id",
            "sample_id",
        }:
            raise _error("authenticated V3 batch sample fields drifted")
        expected_page = next(
            index
            for index, end in enumerate(
                __import__("itertools").accumulate(EXPECTED_LINE_COUNT_VECTOR), start=1
            )
            if ordinal <= end
        )
        page_id = f"page-{expected_page:04d}"
        line_index = counts[expected_page - 1]
        if (
            sample["page_id"] != page_id
            or sample["sample_id"] != f"{page_id}-line-{line_index:04d}"
            or type(sample["crop_png_bytes"]) is not bytes
            or _SHA_RE.fullmatch(sample["crop_sha256"]) is None
            or _sha(sample["crop_png_bytes"]) != sample["crop_sha256"]
        ):
            raise _error("authenticated V3 batch order or crop identity drifted")
        counts[expected_page - 1] += 1
    if counts != list(EXPECTED_LINE_COUNT_VECTOR):
        raise _error("authenticated V3 per-page denominator drifted")
    return canonical_clone_v1(projection), tuple(batch)


def _deny_network_connections() -> None:
    def audit_hook(event: str, _args: tuple[Any, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise RuntimeError("network access is forbidden during formal VietOCR V3 inference")

    sys.addaudithook(audit_hook)


def _merged_model_config(config: dict[str, Any], snapshots: dict[str, bytes]) -> dict[str, Any]:
    try:
        base = yaml.safe_load(snapshots["base_config"].decode("utf-8"))
        model = yaml.safe_load(snapshots["model_config"].decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _error("VietOCR YAML snapshots cannot be decoded") from exc
    if type(base) is not dict or type(model) is not dict:
        raise _error("VietOCR YAML snapshots must be objects")
    merged = dict(base)
    merged.update(model)
    merged["device"] = config["inference"]["device"]
    merged["weights"] = "IN_MEMORY_AUTHENTICATED_WEIGHTS_SNAPSHOT"
    merged["predictor"] = dict(merged.get("predictor", {}))
    merged["predictor"]["beamsearch"] = False
    merged["cnn"] = dict(merged.get("cnn", {}))
    merged["cnn"]["pretrained"] = False
    if merged.get("backbone") != "vgg19_bn" or merged.get("seq_modeling") != "transformer":
        raise _error("VietOCR YAML architecture differs from VGG Transformer")
    return merged


def _assert_float32_model(torch: Any, model: Any) -> None:
    for label, values in (("parameter", model.parameters()), ("buffer", model.buffers())):
        for value in values:
            if value.is_floating_point() and value.dtype != torch.float32:
                raise _error(f"VietOCR {label} is not FP32")


def _execute_model(
    project_root: Path,
    config: dict[str, Any],
    snapshots: dict[str, bytes],
    batch: tuple[dict[str, Any], ...],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int], dict[str, float]]:
    if any(name == "vietocr" or name.startswith("vietocr.") for name in sys.modules):
        raise _error("VietOCR was imported before the authenticated overlay check")
    site_packages = RUNTIME_ROOT / config["runtime"]["site_packages"]
    _verify_wheel_overlay(snapshots["wheel"], site_packages)
    private_overlay = _materialize_private_wheel_overlay(
        snapshots["wheel"], project_root / "output/development"
    )
    sys.path.insert(0, private_overlay.as_posix())
    _deny_network_connections()
    try:
        import torch
        from vietocr.tool.translate import build_model, process_input, translate

        imported = sys.modules.get("vietocr.tool.translate")
        if (
            imported is None
            or imported.__spec__ is None
            or not str(imported.__spec__.origin).startswith(private_overlay.as_posix())
        ):
            raise _error("VietOCR executable modules did not load from the private wheel snapshot")

        packages = {name: importlib.metadata.version(name) for name in sorted(_EXPECTED_PACKAGES)}
        if packages != _EXPECTED_PACKAGES:
            raise _error("formal VietOCR runtime package identity drifted")
        if (
            f"{sys.version_info.major}.{sys.version_info.minor}" != "3.11"
            or torch.__version__ != "2.12.0+cu130"
            or torch.version.cuda != "13.0"
            or not torch.cuda.is_available()
            or torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4090"
            or tuple(torch.cuda.get_device_capability(0)) != (8, 9)
        ):
            raise _error("formal VietOCR CUDA/Python/device identity drifted")
        torch.manual_seed(config["inference"]["random_seed"])
        torch.cuda.manual_seed_all(config["inference"]["random_seed"])
        torch.set_default_dtype(torch.float32)
        if torch.get_default_dtype() != torch.float32:
            raise _error("PyTorch default floating dtype is not FP32")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.set_float32_matmul_precision("highest")
        if torch.is_autocast_enabled() or torch.is_autocast_enabled("cuda"):
            raise _error("autocast is unexpectedly enabled")
        merged = _merged_model_config(config, snapshots)
        started = time.perf_counter()
        model, vocab = build_model(merged)
        counts = {
            "authenticated_batch_accessor_call_count": 1,
            "checkpoint_deserialization_count": 0,
            "formal_run_count": 1,
            "model_build_count": 1,
            "process_input_count": 0,
            "reader_request_count": 1,
            "result_count": 0,
            "state_dict_load_count": 0,
            "translate_call_count": 0,
        }
        if (
            hasattr(model, "_orig_mod")
            or type(model).__module__.startswith("torch.jit")
            or "OptimizedModule" in type(model).__name__
            or "ScriptModule" in type(model).__name__
        ):
            raise _error("VietOCR model is not a plain eager PyTorch module")
        model.float()
        _assert_float32_model(torch, model)
        state = torch.load(
            io.BytesIO(snapshots["weights"]),
            map_location=torch.device(merged["device"]),
            weights_only=True,
        )
        counts["checkpoint_deserialization_count"] += 1
        for value in state.values():
            if hasattr(value, "is_floating_point") and value.is_floating_point():
                if value.dtype != torch.float32:
                    raise _error("VietOCR checkpoint contains a non-FP32 tensor")
        model.load_state_dict(state)
        counts["state_dict_load_count"] += 1
        model.eval()
        _assert_float32_model(torch, model)
        model_load_seconds = time.perf_counter() - started
        results: list[dict[str, Any]] = []
        with torch.inference_mode():
            for sample in batch:
                with Image.open(io.BytesIO(sample["crop_png_bytes"])) as raw:
                    image = raw.convert("RGB")
                tensor = process_input(
                    image,
                    int(merged["dataset"]["image_height"]),
                    int(merged["dataset"]["image_min_width"]),
                    int(merged["dataset"]["image_max_width"]),
                ).to(device=merged["device"], dtype=torch.float32)
                counts["process_input_count"] += 1
                if tensor.dtype != torch.float32 or torch.is_autocast_enabled("cuda"):
                    raise _error("VietOCR input tensor is not strict FP32")
                sentence, probabilities = translate(
                    tensor,
                    model,
                    max_seq_length=config["inference"]["max_sequence_length"],
                )
                counts["translate_call_count"] += 1
                prediction = vocab.decode(sentence[0].tolist())
                probability = float(probabilities[0])
                if (
                    type(prediction) is not str
                    or not math.isfinite(probability)
                    or not (0.0 <= probability <= 1.0)
                ):
                    raise _error("VietOCR decoded proposal is malformed")
                results.append(
                    {
                        "crop_sha256": sample["crop_sha256"],
                        "mean_decoded_character_probability": probability,
                        "page_id": sample["page_id"],
                        "processed_height": int(tensor.shape[-2]),
                        "processed_width": int(tensor.shape[-1]),
                        "raw_prediction": prediction,
                        "sample_id": sample["sample_id"],
                    }
                )
                counts["result_count"] += 1
                del tensor
        torch.cuda.synchronize()
        if (
            torch.get_default_dtype() != torch.float32
            or torch.is_autocast_enabled()
            or torch.is_autocast_enabled("cuda")
            or torch.backends.cuda.matmul.allow_tf32
            or torch.backends.cudnn.allow_tf32
        ):
            raise _error("PyTorch eager FP32 policy drifted during inference")
        _assert_float32_model(torch, model)
        expected_counts = {
            "authenticated_batch_accessor_call_count": 1,
            "checkpoint_deserialization_count": 1,
            "formal_run_count": 1,
            "model_build_count": 1,
            "process_input_count": EXPECTED_SAMPLE_COUNT,
            "reader_request_count": 1,
            "result_count": EXPECTED_SAMPLE_COUNT,
            "state_dict_load_count": 1,
            "translate_call_count": EXPECTED_SAMPLE_COUNT,
        }
        if counts != expected_counts:
            raise _error("formal VietOCR execution counts drifted")
        _verify_wheel_overlay(snapshots["wheel"], site_packages)
        runtime = {
            "compute_capability": "8.9",
            "cuda_runtime": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(0),
            "packages": packages,
            "python_major_minor": "3.11",
            "runtime_root": RUNTIME_ROOT.as_posix(),
        }
        metrics = {
            "model_load_seconds": model_load_seconds,
            "peak_gpu_memory_allocated_mib": torch.cuda.max_memory_allocated() / (1024**2),
            "peak_gpu_memory_reserved_mib": torch.cuda.max_memory_reserved() / (1024**2),
            "total_wall_seconds": time.perf_counter() - started,
        }
        return results, runtime, counts, metrics
    finally:
        if private_overlay.as_posix() in sys.path:
            sys.path.remove(private_overlay.as_posix())
        for name in tuple(sys.modules):
            if name == "vietocr" or name.startswith("vietocr.") or name == "config":
                sys.modules.pop(name, None)
        shutil.rmtree(private_overlay)


def _write_exclusive(directory_fd: int, name: str, payload: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o444,
        dir_fd=directory_fd,
    )
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise _error(f"short exclusive write: {name}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_executor_outputs(
    results: Any,
    runtime: Any,
    counts: Any,
    metrics: Any,
    batch: tuple[dict[str, Any], ...],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int], dict[str, float]]:
    expected_counts = {
        "authenticated_batch_accessor_call_count": 1,
        "checkpoint_deserialization_count": 1,
        "formal_run_count": 1,
        "model_build_count": 1,
        "process_input_count": EXPECTED_SAMPLE_COUNT,
        "reader_request_count": 1,
        "result_count": EXPECTED_SAMPLE_COUNT,
        "state_dict_load_count": 1,
        "translate_call_count": EXPECTED_SAMPLE_COUNT,
    }
    if type(results) is not list or len(results) != EXPECTED_SAMPLE_COUNT:
        raise _error("formal VietOCR result denominator drifted")
    result_fields = {
        "crop_sha256",
        "mean_decoded_character_probability",
        "page_id",
        "processed_height",
        "processed_width",
        "raw_prediction",
        "sample_id",
    }
    for result, sample in zip(results, batch, strict=True):
        if (
            type(result) is not dict
            or set(result) != result_fields
            or result["sample_id"] != sample["sample_id"]
            or result["page_id"] != sample["page_id"]
            or result["crop_sha256"] != sample["crop_sha256"]
            or type(result["raw_prediction"]) is not str
            or type(result["processed_width"]) is not int
            or result["processed_width"] <= 0
            or type(result["processed_height"]) is not int
            or result["processed_height"] <= 0
            or type(result["mean_decoded_character_probability"]) is not float
            or not math.isfinite(result["mean_decoded_character_probability"])
            or not 0.0 <= result["mean_decoded_character_probability"] <= 1.0
        ):
            raise _error("formal VietOCR result differs from its authenticated input")
    if (
        type(counts) is not dict
        or counts != expected_counts
        or any(type(value) is not int for value in counts.values())
    ):
        raise _error("formal VietOCR execution counts drifted")
    expected_runtime_fields = {
        "compute_capability",
        "cuda_runtime",
        "device_name",
        "packages",
        "python_major_minor",
        "runtime_root",
    }
    if (
        type(runtime) is not dict
        or set(runtime) != expected_runtime_fields
        or runtime["compute_capability"] != "8.9"
        or runtime["cuda_runtime"] != "13.0"
        or runtime["device_name"] != "NVIDIA GeForce RTX 4090"
        or runtime["packages"] != _EXPECTED_PACKAGES
        or runtime["python_major_minor"] != "3.11"
        or runtime["runtime_root"] != RUNTIME_ROOT.as_posix()
    ):
        raise _error("formal VietOCR runtime evidence drifted")
    metric_fields = {
        "model_load_seconds",
        "peak_gpu_memory_allocated_mib",
        "peak_gpu_memory_reserved_mib",
        "total_wall_seconds",
    }
    if (
        type(metrics) is not dict
        or set(metrics) != metric_fields
        or any(
            type(value) is not float or not math.isfinite(value) or value < 0.0
            for value in metrics.values()
        )
    ):
        raise _error("formal VietOCR runtime metrics drifted")
    return results, runtime, counts, metrics


def _create_attempt_root(root: Path, attempt_payload: bytes) -> tuple[int, int, tuple[int, int]]:
    development = root / "output/development"
    if not development.is_dir() or development.is_symlink():
        raise _error("fixed output/development root is unsafe")
    parent_name = RUN_ROOT.parent.name
    development_fd = os.open(
        development,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        try:
            os.mkdir(parent_name, 0o700, dir_fd=development_fd)
            os.fsync(development_fd)
        except FileExistsError:
            pass
        parent_fd = os.open(
            parent_name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=development_fd,
        )
    finally:
        os.close(development_fd)
    try:
        os.mkdir(RUN_ROOT.name, 0o700, dir_fd=parent_fd)
        run_fd = os.open(
            RUN_ROOT.name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    except BaseException:
        os.close(parent_fd)
        raise
    try:
        _write_exclusive(run_fd, _ATTEMPT_NAME, attempt_payload)
        os.fsync(run_fd)
    except BaseException:
        os.close(run_fd)
        os.close(parent_fd)
        raise
    opened = os.fstat(run_fd)
    identity = (opened.st_dev, opened.st_ino)
    named = os.stat(RUN_ROOT.name, dir_fd=parent_fd, follow_symlinks=False)
    if (named.st_dev, named.st_ino) != identity:
        os.close(run_fd)
        os.close(parent_fd)
        raise _error("formal V3 run root inode changed during attempt publication")
    return run_fd, parent_fd, identity


def run_authenticated_vietocr_all_line_v3(
    project_root: Path,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> dict[str, Any]:
    """Execute the sole fixed 835-sample VGG Transformer attempt."""

    root = _resolve_root(project_root)
    assert_authenticated_vietocr_all_line_freeze_project_root_v3(root, freeze_capability)
    if os.path.lexists(root / RUN_ROOT):
        raise _error("formal V3 run root already exists; resume and retry are forbidden")
    git_before = _git_binding(root)
    config_payload = _stable_bytes(root / CONFIG_PATH, "V3 VietOCR configuration")
    config = _validate_config(config_payload)
    projection, batch = _collect_freeze(freeze_capability)
    snapshots, runtime_artifacts = _snapshot_runtime(config)
    _verify_wheel_overlay(snapshots["wheel"], RUNTIME_ROOT / "site-packages")
    preflight = {
        "configuration_ref": {
            "path": CONFIG_PATH.as_posix(),
            "sha256": _sha(config_payload),
            "size_bytes": len(config_payload),
        },
        "execution_policy": _EXECUTION_POLICY,
        "experiment_id": EXPERIMENT_ID,
        "freeze_id": projection["freeze_id"],
        "git_binding": git_before,
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "runtime_artifacts": runtime_artifacts,
        "sample_count": EXPECTED_SAMPLE_COUNT,
    }
    attempt_id = f"voalrv3:attempt:{canonical_json_sha256_v1(preflight)}"
    started_at = datetime.now(UTC).isoformat()
    attempt = {
        "attempt_id": attempt_id,
        "claim_boundary": "FRESH_REFERENCE_BLIND_SEMANTIC_PROPOSAL_ATTEMPT_ONLY",
        "format_version": ATTEMPT_FORMAT_VERSION,
        "preflight": preflight,
        "started_at": started_at,
        "state": "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY",
    }
    attempt_payload = canonical_json_bytes_v1(attempt)
    run_fd, run_parent_fd, run_identity = _create_attempt_root(root, attempt_payload)
    try:
        results, runtime, counts, metrics = _execute_model(root, config, snapshots, batch)
        results, runtime, counts, metrics = _validate_executor_outputs(
            results, runtime, counts, metrics, batch
        )
        if _stable_bytes(root / CONFIG_PATH, "V3 VietOCR configuration") != config_payload:
            raise _error("V3 VietOCR configuration changed during inference")
        current_snapshots, current_artifacts = _snapshot_runtime(config)
        if current_snapshots != snapshots or current_artifacts != runtime_artifacts:
            raise _error("VietOCR runtime artifacts changed during inference")
        git_after = _git_binding(root)
        if git_after != git_before:
            raise _error("Git provenance changed during formal VietOCR inference")
        completed_at = datetime.now(UTC).isoformat()
        result_material = {
            "attempt_id": attempt_id,
            "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
            "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
            "experiment_id": EXPERIMENT_ID,
            "format_version": RESULT_FORMAT_VERSION,
            "freeze_id": projection["freeze_id"],
            "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
            "page_count": 8,
            "reference_text_available_to_reader": False,
            "sample_count": EXPECTED_SAMPLE_COUNT,
            "samples": results,
            "state": "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE",
        }
        result_id = f"voalrv3:result:{canonical_json_sha256_v1(result_material)}"
        result = {**result_material, "result_id": result_id}
        result_payload = canonical_json_bytes_v1(result)
        result_ref = {
            "path": f"{RUN_ROOT.as_posix()}/{_RESULT_NAME}",
            "sha256": _sha(result_payload),
            "size_bytes": len(result_payload),
        }
        attempt_ref = {
            "path": f"{RUN_ROOT.as_posix()}/{_ATTEMPT_NAME}",
            "sha256": _sha(attempt_payload),
            "size_bytes": len(attempt_payload),
        }
        run_material = {
            "artifacts": {"attempt": attempt_ref, "ocr_result": result_ref},
            "attempt_id": attempt_id,
            "completed_at": completed_at,
            "configuration": preflight["configuration_ref"],
            "execution_counts": counts,
            "execution_policy": _EXECUTION_POLICY,
            "experiment_id": EXPERIMENT_ID,
            "format_version": RUN_FORMAT_VERSION,
            "git_binding": git_before,
            "input": {
                "freeze_id": projection["freeze_id"],
                "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
                "page_count": 8,
                "sample_count": EXPECTED_SAMPLE_COUNT,
            },
            "metrics": metrics,
            "result_id": result_id,
            "runtime": {**runtime, "artifacts": runtime_artifacts},
            "safety": _SAFETY,
            "started_at": started_at,
            "state": "FRESH_SINGLE_RUN_COMPLETE",
        }
        run_id = f"voalrv3:run:{canonical_json_sha256_v1(run_material)}"
        manifest = {**run_material, "run_id": run_id}
        manifest_payload = canonical_json_bytes_v1(manifest)
        _write_exclusive(run_fd, _RESULT_NAME, result_payload)
        _write_exclusive(run_fd, _RUN_NAME, manifest_payload)
        os.fsync(run_fd)
        if (
            sorted(os.listdir(run_fd)) != [_ATTEMPT_NAME, _RESULT_NAME, _RUN_NAME]
            or _read_fd_bytes(run_fd, _ATTEMPT_NAME) != attempt_payload
            or _read_fd_bytes(run_fd, _RESULT_NAME) != result_payload
            or _read_fd_bytes(run_fd, _RUN_NAME) != manifest_payload
        ):
            raise _error("formal VietOCR completed artifacts failed exact readback")
        named = os.stat(RUN_ROOT.name, dir_fd=run_parent_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != run_identity:
            raise _error("official formal VietOCR run root changed during inference")
        return canonical_clone_v1(manifest)
    finally:
        os.close(run_fd)
        os.close(run_parent_fd)
