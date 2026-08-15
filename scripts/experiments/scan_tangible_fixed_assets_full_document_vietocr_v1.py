"""Scan all eight fresh-VietOCR PDFs for tangible fixed-asset movements."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
DEFAULT_RESCUE_ROOT = Path("output/development/vib-page37-rotated-vietocr-v1")
FORMAT_VERSION = "TANGIBLE_FIXED_ASSETS_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "TANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
RESCUE_FORMAT = "ROTATED_VIETOCR_SEMANTIC_RESCUE_PROJECTION_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_SHARED_TANGIBLE_FIXED_ASSET_"
    "OWNER_COST_ACCUMULATED_DEPRECIATION_CARRYING_VALUE_OPTIONAL_MOVEMENTS_"
    "COMPARATIVE_CONTINUATION_AND_ROTATED_SAME_TRANSFORMER_RESCUE_SCAN_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_uses_same_pinned_vietocr_transformer": True,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_axis_projection_id",
    "input_rescue",
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}
_EXPECTED_CONFIG_SHA256 = "aa007448e2ed4f940693c3b4c03ae47111cf1ed00580d13c05a41941e5094119"
_EXPECTED_RESCUE_REFS = {
    "crop_manifest.json": (
        "8f09d17d0842753d92af8d8cfaf1524706bca4b32255b23e21bd744d8384b696",
        55616,
    ),
    "reader-output/ocr_result.json": (
        "191c670afeb410515770bfaed0e08f314d21b21c14ccf467c461993df17c0333",
        49719,
    ),
    "reader-output/run_manifest.json": (
        "81cb77b6d4ddaa37ab29fcdde5bdc87e82bf04be1a27a563584d8934d87ee380",
        3131,
    ),
    "reader_request.json": (
        "5f031314423cf4699d25ed4db2954df774c7c70dab05ce6c5197b2935a62c2b4",
        24867,
    ),
}
_HEX = frozenset("0123456789abcdef")


class TangibleFixedAssetsFullDocumentScanV1Error(ValueError):
    """The semantic axis, rotated rescue or tangible-asset scan drifted."""


def _error(message: str) -> TangibleFixedAssetsFullDocumentScanV1Error:
    return TangibleFixedAssetsFullDocumentScanV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _relative_parts(path: Path) -> tuple[str, ...]:
    if not isinstance(path, Path) or path.is_absolute() or not path.parts:
        raise _error(f"fixed path is not one safe relative path: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"fixed path escapes the project root: {path}")
    return tuple(path.parts)


def _stable_bytes(path: Path) -> bytes:
    parts = _relative_parts(path)
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise _error(f"fixed artifact is not a regular file: {path}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    payload = b"".join(chunks)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise _error(f"fixed artifact changed or was incomplete while reading: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root is not one object")
    return value


def _fixed_json(
    path: Path, expected: tuple[str, int] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(path)
    reference = {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if expected is not None and (reference["sha256"], reference["size_bytes"]) != expected:
        raise _error(f"fixed rotated-rescue artifact identity drifted: {path}")
    return _strict_json(payload, path.as_posix()), reference


def _matcher() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/tangible_fixed_assets_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location("tangible_fixed_assets_matcher_for_scan", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load tangible-fixed-assets matcher: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _document(items: Any, source_sha256: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error("semantic-index document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict
        and type(item.get("source_pdf")) is dict
        and item["source_pdf"].get("sha256") == source_sha256
    ]
    if len(matches) != 1:
        raise _error("rotated rescue does not bind one unique source document")
    return matches[0]


def _page(document: dict[str, Any], physical_page: int) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("semantic-index page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == physical_page
    ]
    if len(matches) != 1:
        raise _error("rotated rescue does not bind one unique source page")
    return matches[0]


def _artifact_ref(path: Path, expected: Any, label: str) -> bytes:
    if (
        type(expected) is not dict
        or set(expected) != {"path", "sha256", "size_bytes"}
        or expected["path"] != path.as_posix()
        or type(expected["size_bytes"]) is not int
    ):
        raise _error(f"{label} reference drifted")
    payload = _stable_bytes(path)
    if len(payload) != expected["size_bytes"] or hashlib.sha256(payload).hexdigest() != _sha256(
        expected["sha256"], label
    ):
        raise _error(f"{label} bytes drifted")
    return payload


def authenticate_rotated_vietocr_semantic_rescue_v1(
    semantic_index: Any, rescue_root: Path = DEFAULT_RESCUE_ROOT
) -> dict[str, Any]:
    """Authenticate one rotation-only same-Transformer semantic rescue."""

    if type(semantic_index) is not dict:
        raise _error("semantic index must be one object")
    manifest_path = rescue_root / "crop_manifest.json"
    request_path = rescue_root / "reader_request.json"
    result_path = rescue_root / "reader-output/ocr_result.json"
    run_path = rescue_root / "reader-output/run_manifest.json"
    manifest, manifest_ref = _fixed_json(manifest_path, _EXPECTED_RESCUE_REFS["crop_manifest.json"])
    request, request_ref = _fixed_json(request_path, _EXPECTED_RESCUE_REFS["reader_request.json"])
    result, result_ref = _fixed_json(
        result_path, _EXPECTED_RESCUE_REFS["reader-output/ocr_result.json"]
    )
    run, run_ref = _fixed_json(run_path, _EXPECTED_RESCUE_REFS["reader-output/run_manifest.json"])
    if (
        set(manifest)
        != {
            "authority",
            "document",
            "format_version",
            "line_count",
            "rotation",
            "samples",
            "source_semantic_index",
        }
        or manifest["format_version"] != "VIB_PAGE37_ROTATED_VIETOCR_CROP_MANIFEST_V1"
        or manifest["rotation"] != "CLOCKWISE_90_DEGREES"
        or manifest["authority"]
        != {
            "bank_or_page_used_as_model_input_label": False,
            "geometry_or_numeric_authority": False,
            "rotation_only": True,
            "semantic_text_proposal_only": True,
        }
        or type(manifest["line_count"]) is not int
        or type(manifest["samples"]) is not list
        or len(manifest["samples"]) != manifest["line_count"]
    ):
        raise _error("rotated crop manifest identity or authority drifted")
    source_index_payload = canonical_json_bytes_v1(semantic_index) + b"\n"
    source_ref = manifest["source_semantic_index"]
    if (
        type(source_ref) is not dict
        or source_ref.get("sha256") != hashlib.sha256(source_index_payload).hexdigest()
        or source_ref.get("size_bytes") != len(source_index_payload)
    ):
        raise _error("rotated rescue source semantic index drifted")
    document_ref = manifest["document"]
    if (
        type(document_ref) is not dict
        or set(document_ref) != {"bank_code", "physical_page", "source_pdf"}
        or type(document_ref["physical_page"]) is not int
        or type(document_ref["source_pdf"]) is not dict
    ):
        raise _error("rotated rescue document locator drifted")
    source_sha256 = _sha256(document_ref["source_pdf"].get("sha256"), "source PDF")
    document = _document(semantic_index.get("documents"), source_sha256)
    if not same_typed_json_v1(document.get("source_pdf"), document_ref["source_pdf"]):
        raise _error("rotated rescue source PDF identity drifted")
    page = _page(document, document_ref["physical_page"])
    lines = page.get("lines")
    if type(lines) is not list or len(lines) != manifest["line_count"]:
        raise _error("rotated rescue source line denominator drifted")

    if (
        request.get("format_version") != 2
        or request.get("experiment_id") != "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1"
        or request.get("state") != "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE"
        or request.get("reference_text_available_to_reader") is not False
        or request.get("git_dirty") is not False
        or request.get("sample_count") != manifest["line_count"]
        or request.get("crop_manifest")
        != {"path": manifest_ref["path"], "sha256": manifest_ref["sha256"]}
        or type(request.get("samples")) is not list
    ):
        raise _error("rotated rescue reader request drifted")
    if (
        result.get("format_version") != 2
        or result.get("experiment_id") != request["experiment_id"]
        or result.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result.get("reference_text_available_to_reader") is not False
        or result.get("sample_count") != manifest["line_count"]
        or type(result.get("samples")) is not list
    ):
        raise _error("rotated rescue reader result drifted")
    if (
        run.get("format_version") != 2
        or run.get("experiment_id") != request["experiment_id"]
        or run.get("state") != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or run.get("git_dirty") is not False
        or run.get("git_commit") != request.get("git_commit")
        or run.get("request") != {"path": request_ref["path"], "sha256": request_ref["sha256"]}
        or run.get("configuration", {}).get("sha256") != _EXPECTED_CONFIG_SHA256
        or run.get("runtime", {}).get("packages", {}).get("vietocr") != "0.3.13"
        or run.get("runtime", {}).get("compute_capability") != "8.9"
        or run.get("artifacts", {}).get("ocr_result")
        != {
            "path": "ocr_result.json",
            "sha256": result_ref["sha256"],
            "size_bytes": result_ref["size_bytes"],
        }
        or any(run.get("safety", {}).values())
    ):
        raise _error("rotated rescue run identity, model or safety drifted")

    samples = []
    for index, (raw_manifest, raw_request, raw_result, source_line) in enumerate(
        zip(
            manifest["samples"],
            request["samples"],
            result["samples"],
            lines,
            strict=True,
        )
    ):
        if (
            type(raw_manifest) is not dict
            or set(raw_manifest)
            != {
                "rotated_crop_ref",
                "rotation",
                "sample_id",
                "source_bbox_raw_pixels",
                "source_crop_ref",
                "source_line_index",
            }
            or raw_manifest["source_line_index"] != index
            or raw_manifest["rotation"] != "CLOCKWISE_90_DEGREES"
            or source_line.get("source_line_index") != index
            or not same_typed_json_v1(raw_manifest["source_crop_ref"], source_line.get("crop_ref"))
            or not same_typed_json_v1(
                raw_manifest["source_bbox_raw_pixels"], source_line.get("source_bbox_raw_pixels")
            )
        ):
            raise _error("rotated rescue source line binding drifted")
        rotated_ref = raw_manifest["rotated_crop_ref"]
        rotated_path = Path(rotated_ref.get("path", "")) if type(rotated_ref) is dict else Path()
        _artifact_ref(rotated_path, rotated_ref, "rotated crop")
        expected_request = {
            "category": "VIB_PAGE37_ROTATED_LINE",
            "crop_path": rotated_ref["path"],
            "crop_sha256": rotated_ref["sha256"],
            "sample_id": raw_manifest["sample_id"],
        }
        if not same_typed_json_v1(raw_request, expected_request):
            raise _error("rotated rescue request sample drifted")
        probability = raw_result.get("mean_decoded_character_probability")
        if (
            type(raw_result) is not dict
            or raw_result.get("sample_id") != raw_manifest["sample_id"]
            or raw_result.get("crop_path") != rotated_ref["path"]
            or raw_result.get("crop_sha256") != rotated_ref["sha256"]
            or type(raw_result.get("raw_prediction")) is not str
            or type(raw_result.get("processed_width")) is not int
            or type(raw_result.get("processed_height")) is not int
            or raw_result["processed_width"] <= 0
            or raw_result["processed_height"] <= 0
            or not (
                probability is None
                or (
                    type(probability) is float
                    and math.isfinite(probability)
                    and 0.0 <= probability <= 1.0
                )
            )
        ):
            raise _error("rotated rescue result sample drifted")
        samples.append(
            {
                "mean_decoded_character_probability": probability,
                "rotated_crop_ref": canonical_clone_v1(rotated_ref),
                "semantic_text": raw_result["raw_prediction"],
                "source_crop_sha256": source_line["crop_ref"]["sha256"],
                "source_line_index": index,
            }
        )
    material = {
        "authority": {
            "bank_or_page_used_as_matching_rule": False,
            "mapping_or_numeric_authority": False,
            "reference_text_available_to_reader": False,
            "rotation_only_same_transformer_semantic_rescue": True,
        },
        "format_version": RESCUE_FORMAT,
        "input_refs": {
            "crop_manifest": manifest_ref,
            "ocr_result": result_ref,
            "reader_request": request_ref,
            "run_manifest": run_ref,
        },
        "line_count": len(samples),
        "physical_page": document_ref["physical_page"],
        "samples": samples,
        "source_pdf_sha256": source_sha256,
        "source_projection_sha256": page["source_projection"]["sha256"],
    }
    return {
        **material,
        "rescue_id": "rvtsrv1:rescue:" + canonical_json_sha256_v1(material),
    }


def _matcher_pages(
    document: dict[str, Any], rescue: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], int]:
    applies = rescue is not None and document["source_pdf"]["sha256"] == rescue["source_pdf_sha256"]
    rescue_by_index = (
        {sample["source_line_index"]: sample for sample in rescue["samples"]} if applies else {}
    )
    applied_count = 0
    pages = []
    for page in document["pages"]:
        rescue_page = applies and page["page_sequence"] == rescue["physical_page"]
        lines = []
        for line in page["lines"]:
            sample = rescue_by_index.get(line["source_line_index"]) if rescue_page else None
            if sample is not None:
                semantic_text = sample["semantic_text"]
                semantic_source = "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
                applied_count += 1
            else:
                semantic_text = line["vietocr_text"]
                semantic_source = "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
            lines.append(
                {
                    "bbox": line["bbox"],
                    "semantic_text": semantic_text,
                    "semantic_text_source": semantic_source,
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": line["vietocr_text"],
                }
            )
        pages.append(
            {
                "lines": lines,
                "page_sequence": page["page_sequence"],
                "primary_numeric_authority": page["primary_numeric_authority"],
            }
        )
    if applies and applied_count != rescue["line_count"]:
        raise _error("rotated rescue was not applied to its exact line denominator")
    return pages, applied_count


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
        "unresolved_document_count": len(trials) - unique,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("tangible-fixed-assets scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_TANGIBLE_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or (value["input_rescue"] is not None and type(value["input_rescue"]) is not dict)
    ):
        raise _error("tangible-fixed-assets scan identity or authority drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "rotated_rescue_line_count",
            "source_pdf_sha256",
        }:
            raise _error("tangible-fixed-assets scan trial fields drifted")
        result = trial["matcher_result"]
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["rotated_rescue_line_count"]) is not int
            or type(result) is not dict
            or result.get("format_version") != MATCHER_FORMAT
        ):
            raise _error("tangible-fixed-assets scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("tangible-fixed-assets scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "tfafdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("tangible-fixed-assets scan identity drifted")
    return canonical_clone_v1(value)


def build_tangible_fixed_assets_full_document_scan_v1(
    semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the exact eight-document structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        pages, applied_count = _matcher_pages(document, rescue)
        result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "rotated_rescue_line_count": applied_count,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    rescue_ref = (
        None
        if rescue is None
        else {
            "input_refs": canonical_clone_v1(rescue["input_refs"]),
            "line_count": rescue["line_count"],
            "rescue_id": rescue["rescue_id"],
            "source_pdf_sha256": rescue["source_pdf_sha256"],
            "source_projection_sha256": rescue["source_projection_sha256"],
        }
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_rescue": rescue_ref,
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "FULL_DOCUMENT_TANGIBLE_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "tfafdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_tangible_fixed_assets_full_document_scan_replay_v1(
    value: Any, semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_tangible_fixed_assets_full_document_scan_v1(semantic_index, rescue)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("tangible-fixed-assets scan does not replay exactly")
    return supplied


def build_live_tangible_fixed_assets_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT, rescue_root: Path = DEFAULT_RESCUE_ROOT
) -> dict[str, Any]:
    semantic_index, _ = _fixed_json(input_path)
    rescue = authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index, rescue_root)
    return build_tangible_fixed_assets_full_document_scan_v1(semantic_index, rescue)


def validate_live_tangible_fixed_assets_full_document_scan_v1(
    value: Any, input_path: Path = DEFAULT_INPUT, rescue_root: Path = DEFAULT_RESCUE_ROOT
) -> dict[str, Any]:
    semantic_index, _ = _fixed_json(input_path)
    rescue = authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index, rescue_root)
    return validate_tangible_fixed_assets_full_document_scan_replay_v1(
        value, semantic_index, rescue
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rescue-root", type=Path, default=DEFAULT_RESCUE_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_tangible_fixed_assets_full_document_scan_v1(args.input, args.rescue_root)
    payload = canonical_json_bytes_v1(result) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
