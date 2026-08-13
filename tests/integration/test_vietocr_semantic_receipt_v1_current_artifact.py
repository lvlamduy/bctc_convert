from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.vietocr_semantic_receipt_v1 import (
    bind_vietocr_semantic_page_v1,
    replay_vietocr_semantic_receipt_v1,
    validate_vietocr_semantic_page_binding_v1,
    validate_vietocr_semantic_receipt_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANARY_ROOT = Path("output/development/lag-v1-semantic-canary/source-only-canary-v1")
CROP_MANIFEST = CANARY_ROOT / "frozen/crop_manifest.json"
READER_REQUEST = CANARY_ROOT / "frozen/reader_request.json"
VIETOCR_RESULT = CANARY_ROOT / "outputs/vietocr-vgg-transformer-rtx4090-v1/ocr_result.json"
RUN_MANIFEST = CANARY_ROOT / "outputs/vietocr-vgg-transformer-rtx4090-v1/run_manifest.json"
TIER1_FIXTURE = Path("tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json")


def _json(relative: Path | str) -> dict:
    return json.loads((PROJECT_ROOT / relative).read_bytes())


def _current_page_inputs_by_result_sha() -> dict[str, tuple[dict, dict]]:
    fixture = _json(TIER1_FIXTURE)
    by_hash: dict[str, tuple[dict, dict]] = {}
    for case in fixture["cases"]:
        provenance = case["provenance_only_not_inference"]
        for page in provenance["page_inputs"]:
            result_ref = page["result_ref"]
            if result_ref is not None:
                by_hash.setdefault(result_ref["sha256"], (provenance, page))
    return by_hash


def _projection(provenance: dict, page: dict) -> dict:
    manifest = _json(provenance["v3_document_manifest_ref"]["path"])
    pointer = page["page_record_json_pointer"]
    assert pointer.startswith("/page_records/")
    record = manifest["page_records"][int(pointer.removeprefix("/page_records/"))]
    result = _json(page["result_ref"]["path"])
    return project_authenticated_page_v2(page_record=record, page_result=result)


def test_current_global_canary_replays_and_all_four_pages_bind_exact_v2_lines() -> None:
    required = [CROP_MANIFEST, READER_REQUEST, VIETOCR_RESULT, RUN_MANIFEST, TIER1_FIXTURE]
    if any(not (PROJECT_ROOT / path).is_file() for path in required):
        pytest.skip("current E-0024 source-only canary is not hydrated")

    receipt = validate_vietocr_semantic_receipt_v1(
        PROJECT_ROOT,
        CROP_MANIFEST,
        READER_REQUEST,
        VIETOCR_RESULT,
        RUN_MANIFEST,
    )
    assert receipt["metrics"] == {
        "page_count": 4,
        "sample_count": 106,
        "single_line_sample_count": 93,
        "diagnostic_union_sample_count": 13,
    }
    assert (
        replay_vietocr_semantic_receipt_v1(
            PROJECT_ROOT,
            CROP_MANIFEST,
            READER_REQUEST,
            VIETOCR_RESULT,
            RUN_MANIFEST,
            receipt,
        )
        == receipt
    )

    page_inputs = _current_page_inputs_by_result_sha()
    bindings = []
    for page in receipt["pages"]:
        match = page_inputs.get(page["result_ref"]["sha256"])
        assert match is not None
        projection = _projection(*match)
        binding = bind_vietocr_semantic_page_v1(projection, receipt)
        assert binding["page_id"] == page["page_id"]
        assert binding["metrics"]["single_line_sample_count"] == page["single_line_sample_count"]
        assert (
            binding["metrics"]["diagnostic_union_sample_count"]
            == page["diagnostic_union_sample_count"]
        )
        assert validate_vietocr_semantic_page_binding_v1(binding, projection, receipt) == binding
        for sample in binding["samples"]:
            assert sample["diagnostic_only"] is (sample["grouping"] == "STRICT_ADJACENT_UNION")
            assert [atom["line_index"] for atom in sample["source_atoms"]] == sample[
                "source_line_indices"
            ]
            atom_boxes = [atom["pixel_bbox"] for atom in sample["source_atoms"]]
            assert sample["source_bbox_raw_pixels"] == [
                min(box[0] for box in atom_boxes),
                min(box[1] for box in atom_boxes),
                max(box[2] for box in atom_boxes),
                max(box[3] for box in atom_boxes),
            ]
        bindings.append(binding)

    assert sum(item["metrics"]["sample_count"] for item in bindings) == 106
    assert sum(item["metrics"]["diagnostic_union_sample_count"] for item in bindings) == 13
    assert all(item["safety"]["semantic_acceptance"] is False for item in bindings)
