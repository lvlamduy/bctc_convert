"""Shared eager-FP32 VietOCR kernel for authenticated crop-byte sessions.

The kernel knows nothing about banks, files, pages, periods, schemas, labels or
expected text.  It opens one authenticated archive session, consumes every
opaque crop in order exactly once, and emits semantic proposals through a
caller-supplied sink.  The pinned VGG Transformer runtime helpers are shared
with the audited V3 runner; family-specific code never reimplements model or
precision policy.
"""

from __future__ import annotations

import importlib.metadata
import io
import math
import shutil
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (
    AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    read_authenticated_family_first_semantic_label_chunk_v1,
)
from bctc_ai.ocr import vietocr_all_line_runner_v3 as runtime_v3

__all__ = [
    "VietOCRReferenceBlindKernelV1Error",
    "execute_authenticated_vietocr_reference_blind_v1",
    "preflight_authenticated_vietocr_runtime_v1",
]


class VietOCRReferenceBlindKernelV1Error(RuntimeError):
    """The authenticated crop session or eager-FP32 model execution drifted."""


def _error(message: str) -> VietOCRReferenceBlindKernelV1Error:
    return VietOCRReferenceBlindKernelV1Error(message)


def _preflight_package_versions() -> dict[str, str]:
    """Read ambient dependencies before the private VietOCR wheel exists.

    VietOCR itself is deliberately absent from the ambient environment.  Its
    exact wheel bytes and installed overlay are authenticated below, then the
    complete package ledger is observed again after that wheel is materialized
    into the private execution overlay.  Asking ``importlib.metadata`` for
    VietOCR here would incorrectly require an unauthenticated ambient install.
    """

    packages = {"vietocr": runtime_v3._EXPECTED_PACKAGES["vietocr"]}
    try:
        packages.update(
            {
                name: importlib.metadata.version(name)
                for name in sorted(runtime_v3._EXPECTED_PACKAGES)
                if name != "vietocr"
            }
        )
    except importlib.metadata.PackageNotFoundError as exc:
        raise _error("formal VietOCR ambient dependency metadata is unavailable") from exc
    return dict(sorted(packages.items()))


def preflight_authenticated_vietocr_runtime_v1(config_payload: bytes) -> dict[str, Any]:
    """Reject a wrong Python/GPU/package environment before staking an attempt."""

    config = runtime_v3._validate_config(config_payload)
    if any(name == "vietocr" or name.startswith("vietocr.") for name in sys.modules):
        raise _error("VietOCR was imported before the authenticated private overlay")
    try:
        import torch
    except ImportError as exc:
        raise _error("formal VietOCR runtime does not provide pinned PyTorch") from exc
    packages = _preflight_package_versions()
    if (
        packages != runtime_v3._EXPECTED_PACKAGES
        or f"{sys.version_info.major}.{sys.version_info.minor}" != "3.11"
        or torch.__version__ != "2.12.0+cu130"
        or torch.version.cuda != "13.0"
        or not torch.cuda.is_available()
        or torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4090"
        or tuple(torch.cuda.get_device_capability(0)) != (8, 9)
    ):
        raise _error("formal VietOCR Python/package/CUDA/device identity drifted")
    snapshots, records = runtime_v3._snapshot_runtime(config)
    runtime_v3._verify_wheel_overlay(
        snapshots["wheel"], runtime_v3.RUNTIME_ROOT / config["runtime"]["site_packages"]
    )
    return {"configuration": config, "runtime_artifacts": records, "snapshots": snapshots}


def execute_authenticated_vietocr_reference_blind_v1(
    project_root: Path,
    reader_session: AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    *,
    expected_sample_count: int,
    config: dict[str, Any],
    runtime_snapshots: dict[str, bytes],
    result_sink: Callable[[dict[str, Any]], None],
    chunk_size: int = 256,
) -> tuple[dict[str, Any], dict[str, int], dict[str, float]]:
    """Run one model load and emit every ordered semantic proposal once."""

    if type(reader_session) is not AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
        raise _error("reference-blind kernel requires one exact live reader session")
    if not isinstance(project_root, Path) or not callable(result_sink):
        raise _error("reference-blind kernel inputs are malformed")
    if type(chunk_size) is not int or not 1 <= chunk_size <= 4096:
        raise _error("reference-blind kernel chunk size must be an integer in [1,4096]")
    if type(expected_sample_count) is not int or expected_sample_count <= 0:
        raise _error("reference-blind kernel sample denominator must be one positive integer")
    if any(name == "vietocr" or name.startswith("vietocr.") for name in sys.modules):
        raise _error("VietOCR was imported before the authenticated private overlay")
    site_packages = runtime_v3.RUNTIME_ROOT / config["runtime"]["site_packages"]
    runtime_v3._verify_wheel_overlay(runtime_snapshots["wheel"], site_packages)
    private_overlay = runtime_v3._materialize_private_wheel_overlay(
        runtime_snapshots["wheel"], project_root / "output/development"
    )
    sys.path.insert(0, private_overlay.as_posix())
    runtime_v3._deny_network_connections()
    try:
        import torch
        from vietocr.tool.translate import build_model, process_input, translate

        imported = sys.modules.get("vietocr.tool.translate")
        if (
            imported is None
            or imported.__spec__ is None
            or not str(imported.__spec__.origin).startswith(private_overlay.as_posix())
        ):
            raise _error("VietOCR executable modules did not load from the private wheel")
        packages = {
            name: importlib.metadata.version(name) for name in sorted(runtime_v3._EXPECTED_PACKAGES)
        }
        if (
            packages != runtime_v3._EXPECTED_PACKAGES
            or f"{sys.version_info.major}.{sys.version_info.minor}" != "3.11"
            or torch.__version__ != "2.12.0+cu130"
            or torch.version.cuda != "13.0"
            or not torch.cuda.is_available()
            or torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4090"
            or tuple(torch.cuda.get_device_capability(0)) != (8, 9)
        ):
            raise _error("formal VietOCR runtime identity drifted after attempt start")
        torch.manual_seed(config["inference"]["random_seed"])
        torch.cuda.manual_seed_all(config["inference"]["random_seed"])
        torch.set_default_dtype(torch.float32)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.set_float32_matmul_precision("highest")
        if (
            torch.get_default_dtype() != torch.float32
            or torch.is_autocast_enabled()
            or torch.is_autocast_enabled("cuda")
        ):
            raise _error("PyTorch eager FP32 precondition drifted")
        merged = runtime_v3._merged_model_config(config, runtime_snapshots)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        model, vocab = build_model(merged)
        counts = {
            "checkpoint_deserialization_count": 0,
            "formal_run_count": 1,
            "model_build_count": 1,
            "process_input_count": 0,
            "reader_chunk_call_count": 0,
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
            raise _error("VietOCR model is not one plain eager PyTorch module")
        model.float()
        runtime_v3._assert_float32_model(torch, model)
        state = torch.load(
            io.BytesIO(runtime_snapshots["weights"]),
            map_location=torch.device(merged["device"]),
            weights_only=True,
        )
        counts["checkpoint_deserialization_count"] += 1
        for value in state.values():
            if (
                hasattr(value, "is_floating_point")
                and value.is_floating_point()
                and value.dtype != torch.float32
            ):
                raise _error("VietOCR checkpoint contains a non-FP32 tensor")
        model.load_state_dict(state)
        counts["state_dict_load_count"] += 1
        model.eval()
        runtime_v3._assert_float32_model(torch, model)
        model_load_seconds = time.perf_counter() - started
        prior_sample_id: str | None = None
        with torch.inference_mode():
            while True:
                chunk = read_authenticated_family_first_semantic_label_chunk_v1(
                    reader_session, maximum_samples=chunk_size
                )
                counts["reader_chunk_call_count"] += 1
                if not chunk:
                    break
                for sample in chunk:
                    expected_sample_id = f"sample-{counts['result_count'] + 1:09d}"
                    if (
                        type(sample) is not dict
                        or set(sample) != {"crop_png_bytes", "crop_sha256", "sample_id"}
                        or sample["sample_id"] != expected_sample_id
                        or prior_sample_id == sample["sample_id"]
                        or type(sample["crop_png_bytes"]) is not bytes
                    ):
                        raise _error("authenticated semantic crop order/shape drifted")
                    prior_sample_id = sample["sample_id"]
                    with Image.open(io.BytesIO(sample["crop_png_bytes"])) as raw:
                        raw.load()
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
                    if type(prediction) is not str:
                        raise _error("VietOCR decoded proposal is not one exact string")
                    if math.isfinite(probability) and not 0.0 <= probability <= 1.0:
                        raise _error("finite VietOCR proposal probability lies outside [0,1]")
                    result_sink(
                        {
                            "crop_sha256": sample["crop_sha256"],
                            "mean_decoded_character_probability": (
                                probability if math.isfinite(probability) else None
                            ),
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
            counts["result_count"] != expected_sample_count
            or counts["process_input_count"] != expected_sample_count
            or counts["translate_call_count"] != expected_sample_count
            or counts["checkpoint_deserialization_count"] != 1
            or counts["state_dict_load_count"] != 1
            or torch.get_default_dtype() != torch.float32
            or torch.is_autocast_enabled()
            or torch.is_autocast_enabled("cuda")
            or torch.backends.cuda.matmul.allow_tf32
            or torch.backends.cudnn.allow_tf32
        ):
            raise _error("formal VietOCR execution denominator or FP32 policy drifted")
        runtime_v3._assert_float32_model(torch, model)
        runtime_v3._verify_wheel_overlay(runtime_snapshots["wheel"], site_packages)
        runtime = {
            "compute_capability": "8.9",
            "cuda_runtime": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(0),
            "packages": packages,
            "python_major_minor": "3.11",
            "runtime_root": runtime_v3.RUNTIME_ROOT.as_posix(),
        }
        metrics = {
            "model_load_seconds": float(model_load_seconds),
            "peak_gpu_memory_allocated_mib": float(torch.cuda.max_memory_allocated() / (1024**2)),
            "peak_gpu_memory_reserved_mib": float(torch.cuda.max_memory_reserved() / (1024**2)),
            "total_wall_seconds": float(time.perf_counter() - started),
        }
        return runtime, counts, metrics
    finally:
        if private_overlay.as_posix() in sys.path:
            sys.path.remove(private_overlay.as_posix())
        for name in tuple(sys.modules):
            if name == "vietocr" or name.startswith("vietocr.") or name == "config":
                sys.modules.pop(name, None)
        shutil.rmtree(private_overlay)
