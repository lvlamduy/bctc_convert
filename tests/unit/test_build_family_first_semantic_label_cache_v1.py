from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import fitz
import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/build_family_first_semantic_label_cache_v1.py"
SPEC = importlib.util.spec_from_file_location("family_first_cache_builder", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class _Result:
    def __init__(self, payload: dict[str, object]) -> None:
        self.json = {"res": payload}


class _Detector:
    def predict(self, image: np.ndarray, *, batch_size: int):
        assert batch_size == 1
        height, width = image.shape[:2]
        return [
            _Result(
                {
                    "dt_polys": [
                        [[5, 5], [width - 5, 5], [width - 5, 20], [5, 20]],
                        [[width - 55, 30], [width - 5, 30], [width - 5, 45], [width - 55, 45]],
                    ],
                    "dt_scores": [0.9, 0.8],
                    "input_path": None,
                    "page_index": None,
                }
            )
        ]


def _pdf() -> bytes:
    document = fitz.open()
    for label in ("ONE", "TWO"):
        page = document.new_page(width=300, height=200)
        page.insert_text((20, 30), label)
    payload = document.tobytes()
    document.close()
    return payload


def _plan() -> dict[str, object]:
    return {
        "documents": [],
        "plan_id": "ffslpv1:plan:" + "1" * 64,
        "render_policy": {"dpi": 72},
    }


def test_document_stage_retains_every_page_and_detector_line(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    stage.mkdir()
    pdf = _pdf()
    document = {
        "document_ordinal": 1,
        "page_count": 2,
        "source_pdf_ref": {
            "path": "opaque.pdf",
            "sha256": __import__("hashlib").sha256(pdf).hexdigest(),
            "size_bytes": len(pdf),
        },
    }

    artifact = builder._build_document_stage(
        plan=_plan(),
        document=document,
        pdf_bytes=pdf,
        detector=_Detector(),
        stage=stage,
    )

    assert artifact["metrics"] == {
        "crop_count": 4,
        "detected_line_count": 4,
        "excluded_detected_line_count": 0,
        "page_count": 2,
    }
    assert len(list(stage.glob("page-*/crops/*.png"))) == 4
    first = builder._strict_canonical_json(stage / "page-0001/page.json", "page")
    assert first["page_freeze"]["metrics"]["excluded_detected_line_count"] == 0
    assert first["authority"]["detector_recognition_text_accessed"] is False
    with Image.open(io.BytesIO((stage / "page-0001/crops/line-0000.png").read_bytes())) as image:
        assert image.mode == "RGB"


def test_detector_payload_uses_in_memory_rgb_and_rejects_provider_shape() -> None:
    image = Image.new("RGB", (100, 60), "white")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    payload = builder._detector_payload(_Detector(), stream.getvalue())

    assert payload["input_path"] is None
    assert len(payload["dt_polys"]) == 2

    class Bad:
        def predict(self, _image, *, batch_size):
            return []

    try:
        builder._detector_payload(Bad(), stream.getvalue())
    except builder.FamilyFirstSemanticLabelCacheV1Error:
        pass
    else:
        raise AssertionError("empty provider result must fail closed")


def test_prepare_publishes_once_without_cleaning_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = {"format_version": "TEST", "plan_id": "ffslpv1:plan:" + "1" * 64}
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUTPUT_ROOT", Path("output/cache"))
    monkeypatch.setattr(builder, "PLAN_PATH", Path("output/cache/plan.json"))
    monkeypatch.setattr(builder, "DOCUMENT_ROOT", Path("output/cache/documents"))
    monkeypatch.setattr(
        builder,
        "build_family_first_semantic_label_plan_v1",
        lambda _root, *, model_cache: plan,
    )

    assert (
        builder.prepare_family_first_semantic_label_cache_v1(model_cache=tmp_path / "models")
        == plan
    )
    assert tmp_path.exists()
    assert builder._strict_canonical_json(tmp_path / "output/cache/plan.json", "plan") == plan

    with pytest.raises(builder.FamilyFirstSemanticLabelCacheV1Error, match="already exists"):
        builder.prepare_family_first_semantic_label_cache_v1(model_cache=tmp_path / "models")
