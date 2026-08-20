from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    ROOT / "docs/experiments/E-0155-annual-2025-currency-risk-bid-gemma4-gpu-text-rescue-v1.json"
)


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_gpu_rescue_receipt_is_content_addressed_and_non_authoritative() -> None:
    value = _receipt()
    material = dict(value)
    identity = material.pop("evaluation_id")
    assert identity == "annual2025crgemma4v1:evaluation:" + canonical_json_sha256_v1(material)
    assert value["authority"] == {
        "accounting_authority": False,
        "broad_corpus_accuracy_claim": False,
        "canonicalization_authority": False,
        "export_authority": False,
        "geometry_authority": False,
        "mapping_authority": False,
        "numeric_authority": False,
        "ocr_text_anchor_diagnostic": True,
        "schema_authority": False,
    }


def test_two_targeted_gpu_crops_rescue_exact_pixel_text() -> None:
    value = _receipt()
    assert [trial["role"] for trial in value["trials"]] == [
        "STATE_INTERNAL",
        "STATE_EXTERNAL",
    ]
    assert value["metrics"] == {
        "full_page_negative_control_count": 1,
        "gemma4_exact_pixel_match_count": 2,
        "targeted_crop_rescue_success_count": 2,
        "trial_count": 2,
        "vietocr_exact_pixel_match_count": 0,
    }
    for trial in value["trials"]:
        assert trial["primary_vietocr_evidence"]["text"] != trial["independent_pixel_text"]
        assert trial["gemma4_text"] == trial["independent_pixel_text"]
        assert trial["gemma4_exact_pixel_match"] is True
        assert trial["vietocr_exact_pixel_match"] is False


def test_model_input_crops_replay_from_the_exact_upright_page() -> None:
    value = _receipt()
    page_ref = value["source_document"]["upright_page_ref"]
    page_path = ROOT / page_ref["path"]
    payload = page_path.read_bytes()
    assert len(payload) == page_ref["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == page_ref["sha256"]
    image = Image.open(io.BytesIO(payload))
    for trial in value["trials"]:
        model_input = trial["gemma4_model_input"]
        buffer = io.BytesIO()
        image.crop(tuple(model_input["crop_bbox_upright_pixels"])).save(buffer, format="PNG")
        crop = buffer.getvalue()
        assert len(crop) == model_input["crop_png_size_bytes"]
        assert hashlib.sha256(crop).hexdigest() == model_input["crop_png_sha256"]


def test_full_page_json_failure_forbids_numeric_promotion() -> None:
    value = _receipt()
    control = value["full_page_negative_control"]
    assert control["exact_table_transcription"] is False
    assert {item["failure"] for item in control["observed_failures"]} == {
        "ONE_DIGIT_SUBSTITUTION",
        "ROW_LABEL_AND_ADJACENT_VALUE_ALIGNMENT_DRIFT",
        "SEMANTIC_WORD_SUBSTITUTION",
    }
    assert value["decision"]["full_page_json_can_supply_numeric_truth"] is False
    assert value["decision"]["gemma_output_can_silently_replace_vietocr_output"] is False
    assert value["decision"]["one_stateless_conversation_per_crop"] is True
