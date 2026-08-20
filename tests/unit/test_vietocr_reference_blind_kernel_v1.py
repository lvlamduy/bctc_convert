from __future__ import annotations

import io
import sys
import types
from contextlib import nullcontext
from importlib.machinery import ModuleSpec
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive
from bctc_ai.ocr import vietocr_reference_blind_kernel_v1 as kernel


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (20, 10), "white").save(output, format="PNG")
    return output.getvalue()


def test_kernel_consumes_one_opaque_session_in_order_and_preserves_nan_as_null(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/development").mkdir(parents=True)
    session = object.__new__(archive.AuthenticatedFamilyFirstSemanticLabelReaderSessionV1)
    chunks = iter(
        [
            (
                {
                    "crop_png_bytes": _png(),
                    "crop_sha256": "1" * 64,
                    "sample_id": "sample-000000001",
                },
                {
                    "crop_png_bytes": _png(),
                    "crop_sha256": "2" * 64,
                    "sample_id": "sample-000000002",
                },
            ),
            (),
        ]
    )
    monkeypatch.setattr(
        kernel,
        "read_authenticated_family_first_semantic_label_chunk_v1",
        lambda _session, *, maximum_samples: next(chunks),
    )
    monkeypatch.setattr(kernel.runtime_v3, "_verify_wheel_overlay", lambda *_args: None)
    monkeypatch.setattr(kernel.runtime_v3, "_deny_network_connections", lambda: None)
    monkeypatch.setattr(
        kernel.runtime_v3,
        "_merged_model_config",
        lambda *_args: {
            "dataset": {"image_height": 32, "image_min_width": 32, "image_max_width": 512},
            "device": "cuda:0",
        },
    )
    monkeypatch.setattr(kernel.runtime_v3, "_assert_float32_model", lambda *_args: None)
    monkeypatch.setattr(
        kernel.importlib.metadata,
        "version",
        lambda name: kernel.runtime_v3._EXPECTED_PACKAGES[name],
    )

    class FakeTensor:
        dtype = "float32"
        shape = (1, 3, 32, 120)

        def to(self, **_kwargs):
            return self

    class FakeSentence:
        def __getitem__(self, _index):
            return self

        def tolist(self):
            return [1]

    class FakeModel:
        def parameters(self):
            return ()

        def buffers(self):
            return ()

        def float(self):
            return self

        def eval(self):
            return self

        def load_state_dict(self, _state):
            return None

    class FakeVocab:
        calls = 0

        def decode(self, _tokens):
            self.calls += 1
            return "" if self.calls == 1 else "Tiền mặt"

    class FakeCuda:
        def manual_seed_all(self, _seed):
            return None

        def is_available(self):
            return True

        def get_device_name(self, _ordinal):
            return "NVIDIA GeForce RTX 4090"

        def get_device_capability(self, _ordinal):
            return (8, 9)

        def empty_cache(self):
            return None

        def reset_peak_memory_stats(self):
            return None

        def synchronize(self):
            return None

        def max_memory_allocated(self):
            return 1024.0

        def max_memory_reserved(self):
            return 2048.0

    torch = types.ModuleType("torch")
    torch.__version__ = "2.12.0+cu130"
    torch.version = types.SimpleNamespace(cuda="13.0")
    torch.cuda = FakeCuda()
    torch.float32 = "float32"
    torch.backends = types.SimpleNamespace(
        cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=False)),
        cudnn=types.SimpleNamespace(allow_tf32=False, benchmark=False, deterministic=True),
    )
    torch.manual_seed = lambda _seed: None
    torch.set_default_dtype = lambda _dtype: None
    torch.get_default_dtype = lambda: "float32"
    torch.set_float32_matmul_precision = lambda _value: None
    torch.is_autocast_enabled = lambda *_args: False
    torch.inference_mode = nullcontext
    torch.device = lambda value: value
    torch.load = lambda *_args, **_kwargs: {}

    translate_module = types.ModuleType("vietocr.tool.translate")
    probabilities = iter((float("nan"), 0.9))
    translate_module.build_model = lambda _config: (FakeModel(), FakeVocab())
    translate_module.process_input = lambda *_args: FakeTensor()
    translate_module.translate = lambda *_args, **_kwargs: (
        FakeSentence(),
        [next(probabilities)],
    )
    vietocr = types.ModuleType("vietocr")
    tool = types.ModuleType("vietocr.tool")

    def materialize(_wheel, parent):
        overlay = parent / "private-wheel"
        overlay.mkdir()
        translate_module.__spec__ = ModuleSpec(
            "vietocr.tool.translate", loader=None, origin=(overlay / "translate.py").as_posix()
        )
        monkeypatch.setitem(sys.modules, "torch", torch)
        monkeypatch.setitem(sys.modules, "vietocr", vietocr)
        monkeypatch.setitem(sys.modules, "vietocr.tool", tool)
        monkeypatch.setitem(sys.modules, "vietocr.tool.translate", translate_module)
        return overlay

    monkeypatch.setattr(kernel.runtime_v3, "_materialize_private_wheel_overlay", materialize)
    results = []
    runtime, counts, metrics = kernel.execute_authenticated_vietocr_reference_blind_v1(
        tmp_path,
        session,
        expected_sample_count=2,
        config={
            "inference": {"random_seed": 1, "max_sequence_length": 128},
            "runtime": {"site_packages": "site-packages"},
        },
        runtime_snapshots={"wheel": b"wheel", "weights": b"weights"},
        result_sink=results.append,
    )

    assert [item["sample_id"] for item in results] == [
        "sample-000000001",
        "sample-000000002",
    ]
    assert results[0]["mean_decoded_character_probability"] is None
    assert results[0]["raw_prediction"] == ""
    assert results[1]["raw_prediction"] == "Tiền mặt"
    assert counts["model_build_count"] == 1
    assert counts["checkpoint_deserialization_count"] == 1
    assert counts["translate_call_count"] == 2
    assert counts["reader_chunk_call_count"] == 2
    assert runtime["device_name"] == "NVIDIA GeForce RTX 4090"
    assert metrics["total_wall_seconds"] >= 0.0
