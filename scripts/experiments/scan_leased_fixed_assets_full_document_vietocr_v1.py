"""Scan all eight fresh-VietOCR PDFs for leased fixed-asset movements."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
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
FORMAT_VERSION = "LEASED_FIXED_ASSETS_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "LEASED_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_SHARED_FIXED_ASSET_ENGINE_LEASED_"
    "OWNER_COST_ACCUMULATED_DEPRECIATION_OPTIONAL_MOVEMENTS_AND_NEGATIVE_"
    "FINANCE_LEASE_POLICY_SERVICE_LOAN_CONTROLS_SCAN_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "generic_finance_lease_text_can_accept_family": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "shared_fixed_asset_variant_engine_used": True,
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


class LeasedFixedAssetsFullDocumentScanV1Error(ValueError):
    """The semantic axis or leased-fixed-assets scan drifted."""


def _error(message: str) -> LeasedFixedAssetsFullDocumentScanV1Error:
    return LeasedFixedAssetsFullDocumentScanV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _support() -> ModuleType:
    return _load_module(
        "tangible_fixed_assets_scan_support_for_leased_assets",
        "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "shared_fixed_assets_matcher_for_leased_assets",
        "tangible_fixed_assets_variant_graph_v1.py",
    )


def _negative_controls(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for page in pages:
        for line in page["lines"]:
            normalized = normalize_vietnamese_anchor_v1(line["semantic_text"])
            if "thue tai chinh" not in normalized:
                continue
            if (
                "tai san co dinh thue tai chinh" in normalized
                or "tscd thue tai chinh" in normalized
            ):
                continue
            controls.append(
                {
                    "normalized_text": normalized,
                    "page_sequence": page["page_sequence"],
                    "semantic_text": line["semantic_text"],
                    "source_line_index": line["source_line_index"],
                }
            )
    return controls


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    complete = sum(trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials)
    near = sum(trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials)
    return {
        "complete_region_count": complete,
        "document_count": len(trials),
        "document_unique_structural_match_count": sum(
            trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
            for trial in trials
        ),
        "mapping_verified_count": 0,
        "near_region_count": near,
        "negative_control_line_count": sum(len(trial["negative_controls"]) for trial in trials),
        "unresolved_document_count": len(trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("leased-fixed-assets scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_LEASED_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or (value["input_rescue"] is not None and type(value["input_rescue"]) is not dict)
    ):
        raise _error("leased-fixed-assets scan identity or authority drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "negative_controls",
            "rotated_rescue_line_count",
            "source_pdf_sha256",
        }:
            raise _error("leased-fixed-assets trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["negative_controls"]) is not list
            or type(trial["rotated_rescue_line_count"]) is not int
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("leased-fixed-assets trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("leased-fixed-assets scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "lfafdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("leased-fixed-assets scan identity drifted")
    return canonical_clone_v1(value)


def build_leased_fixed_assets_full_document_scan_v1(
    semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the exact eight-document leased-assets structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        pages, applied_count = support._matcher_pages(document, rescue)
        result = matcher.build_leased_fixed_assets_variant_graph_document_v1(pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "negative_controls": _negative_controls(pages),
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
        "state": "FULL_DOCUMENT_LEASED_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "lfafdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_leased_fixed_assets_full_document_scan_replay_v1(
    value: Any, semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_leased_fixed_assets_full_document_scan_v1(semantic_index, rescue)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("leased-fixed-assets scan does not replay exactly")
    return supplied


def build_live_leased_fixed_assets_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT, rescue_root: Path = DEFAULT_RESCUE_ROOT
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = support.authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index, rescue_root)
    return build_leased_fixed_assets_full_document_scan_v1(semantic_index, rescue)


def validate_live_leased_fixed_assets_full_document_scan_v1(
    value: Any,
    input_path: Path = DEFAULT_INPUT,
    rescue_root: Path = DEFAULT_RESCUE_ROOT,
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = support.authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index, rescue_root)
    return validate_leased_fixed_assets_full_document_scan_replay_v1(value, semantic_index, rescue)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rescue-root", type=Path, default=DEFAULT_RESCUE_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_leased_fixed_assets_full_document_scan_v1(args.input, args.rescue_root)
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
