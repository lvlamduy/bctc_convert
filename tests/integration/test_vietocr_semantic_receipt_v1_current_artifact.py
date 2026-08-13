from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.vietocr_semantic_receipt_v1 import (
    VietOCRSemanticReceiptV1Error,
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


def _hydrated() -> bool:
    required = [CROP_MANIFEST, READER_REQUEST, VIETOCR_RESULT, RUN_MANIFEST, TIER1_FIXTURE]
    return all((PROJECT_ROOT / path).is_file() for path in required)


@contextmanager
def _temporary_bytes(parent: Path, *, suffix: str, payload: bytes) -> Iterator[Path]:
    directory = PROJECT_ROOT / parent
    descriptor, raw_path = tempfile.mkstemp(
        prefix=".receipt-adversarial-", suffix=suffix, dir=directory
    )
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        yield path.relative_to(PROJECT_ROOT)
    finally:
        path.unlink(missing_ok=True)


@contextmanager
def _temporary_json(parent: Path, payload: dict) -> Iterator[Path]:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    with _temporary_bytes(parent, suffix=".json", payload=encoded) as path:
        yield path


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
    if not _hydrated():
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


def test_current_canary_rejects_a_nonexistent_pinned_weights_file() -> None:
    if not _hydrated():
        pytest.skip("current E-0024 source-only canary is not hydrated")

    run = _json(RUN_MANIFEST)
    original_runtime = Path(run["runtime"]["external_root"])
    with tempfile.TemporaryDirectory(
        prefix=".vietocr-runtime-adversarial-",
        dir=PROJECT_ROOT / "output/development",
    ) as temporary:
        replacement_runtime = Path(temporary)
        (replacement_runtime / run["runtime"]["site_packages"]).mkdir()
        for name in ("wheel", "base_config", "model_config"):
            relative = Path(run["runtime"]["artifacts"][name]["path"])
            destination = replacement_runtime / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(original_runtime / relative, destination)
        run["runtime"]["external_root"] = replacement_runtime.as_posix()
        with _temporary_json(RUN_MANIFEST.parent, run) as changed_run:
            with pytest.raises(
                VietOCRSemanticReceiptV1Error,
                match="(?:cannot read )?runtime artifact weights",
            ):
                validate_vietocr_semantic_receipt_v1(
                    PROJECT_ROOT,
                    CROP_MANIFEST,
                    READER_REQUEST,
                    VIETOCR_RESULT,
                    changed_run,
                )


def test_current_canary_rejects_parsed_pinned_config_safety_drift() -> None:
    if not _hydrated():
        pytest.skip("current E-0024 source-only canary is not hydrated")

    run = _json(RUN_MANIFEST)
    config_path = PROJECT_ROOT / run["configuration"]["path"]
    original = config_path.read_text(encoding="utf-8")
    changed = original.replace(
        "automatic_post_correction = false",
        "automatic_post_correction = true",
        1,
    )
    assert changed != original
    with _temporary_bytes(
        Path("config/models"),
        suffix=".toml",
        payload=changed.encode("utf-8"),
    ) as changed_config:
        run["configuration"]["path"] = changed_config.as_posix()
        run["configuration"]["sha256"] = hashlib.sha256(changed.encode("utf-8")).hexdigest()
        with _temporary_json(RUN_MANIFEST.parent, run) as changed_run:
            with pytest.raises(
                VietOCRSemanticReceiptV1Error,
                match="config.*safety|configuration.*safety",
            ):
                validate_vietocr_semantic_receipt_v1(
                    PROJECT_ROOT,
                    CROP_MANIFEST,
                    READER_REQUEST,
                    VIETOCR_RESULT,
                    changed_run,
                )


def test_current_canary_rejects_an_omitted_eligible_line() -> None:
    if not _hydrated():
        pytest.skip("current E-0024 source-only canary is not hydrated")

    manifest = _json(CROP_MANIFEST)
    omitted_index = next(
        index for index, sample in enumerate(manifest["samples"]) if sample["grouping"] == "LINE"
    )
    omitted = manifest["samples"].pop(omitted_index)
    manifest["sample_count"] -= 1
    page = next(item for item in manifest["pages"] if item["page_id"] == omitted["page_id"])
    page["selected_single_line_count"] -= 1
    with _temporary_json(CROP_MANIFEST.parent, manifest) as changed_manifest:
        with pytest.raises(VietOCRSemanticReceiptV1Error, match="eligible LINE selection"):
            validate_vietocr_semantic_receipt_v1(
                PROJECT_ROOT,
                changed_manifest,
                READER_REQUEST,
                VIETOCR_RESULT,
                RUN_MANIFEST,
            )


def test_current_canary_rejects_an_ineligible_line_in_the_frozen_set() -> None:
    if not _hydrated():
        pytest.skip("current E-0024 source-only canary is not hydrated")

    manifest = _json(CROP_MANIFEST)
    page = manifest["pages"][0]
    selected = {
        sample["source_line_indices"][0]
        for sample in manifest["samples"]
        if sample["page_id"] == page["page_id"] and sample["grouping"] == "LINE"
    }
    ineligible = next(
        index for index in range(page["authenticated_line_count"]) if index not in selected
    )
    sample = next(
        item
        for item in manifest["samples"]
        if item["page_id"] == page["page_id"] and item["grouping"] == "LINE"
    )
    sample["source_line_indices"] = [ineligible]
    sample["sample_id"] = f"{page['page_id']}-line-{ineligible:03d}"
    with _temporary_json(CROP_MANIFEST.parent, manifest) as changed_manifest:
        with pytest.raises(VietOCRSemanticReceiptV1Error, match="eligible LINE selection"):
            validate_vietocr_semantic_receipt_v1(
                PROJECT_ROOT,
                changed_manifest,
                READER_REQUEST,
                VIETOCR_RESULT,
                RUN_MANIFEST,
            )


def test_current_canary_rejects_an_invalid_strict_union() -> None:
    if not _hydrated():
        pytest.skip("current E-0024 source-only canary is not hydrated")

    manifest = _json(CROP_MANIFEST)
    union = next(
        sample for sample in manifest["samples"] if sample["grouping"] == "STRICT_ADJACENT_UNION"
    )
    page_id = union["page_id"]
    selected = [
        sample["source_line_indices"][0]
        for sample in manifest["samples"]
        if sample["page_id"] == page_id and sample["grouping"] == "LINE"
    ]
    invalid_pair = [selected[0], selected[-1]]
    assert invalid_pair != union["source_line_indices"]
    union["source_line_indices"] = invalid_pair
    union["sample_id"] = f"{page_id}-union-{invalid_pair[0]:03d}-{invalid_pair[1]:03d}"
    with _temporary_json(CROP_MANIFEST.parent, manifest) as changed_manifest:
        with pytest.raises(VietOCRSemanticReceiptV1Error, match="strict-union selection"):
            validate_vietocr_semantic_receipt_v1(
                PROJECT_ROOT,
                changed_manifest,
                READER_REQUEST,
                VIETOCR_RESULT,
                RUN_MANIFEST,
            )
