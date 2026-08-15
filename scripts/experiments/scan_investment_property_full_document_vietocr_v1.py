"""Scan all eight fresh-VietOCR PDFs for investment-property movements."""

from __future__ import annotations

import argparse
import importlib.util
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
FORMAT_VERSION = "INVESTMENT_PROPERTY_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "INVESTMENT_PROPERTY_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_SHARED_FIXED_ASSET_ENGINE_"
    "INVESTMENT_PROPERTY_OWNER_COST_ACCUMULATED_DEPRECIATION_CARRYING_VALUE_"
    "SAME_PAGE_CURRENT_COMPARATIVE_PERIOD_PARTITION_SCAN_ONLY_NO_NUMERIC_"
    "SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "latest_explicit_period_selects_current_region": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "same_page_comparative_region_retained": True,
    "shared_fixed_asset_variant_engine_used": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_axis_projection_id",
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}


class InvestmentPropertyFullDocumentScanV1Error(ValueError):
    """The semantic axis or investment-property scan drifted."""


def _error(message: str) -> InvestmentPropertyFullDocumentScanV1Error:
    return InvestmentPropertyFullDocumentScanV1Error(message)


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
        "tangible_fixed_assets_scan_support_for_investment_property",
        "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "shared_fixed_assets_matcher_for_investment_property",
        "tangible_fixed_assets_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    complete = sum(trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials)
    comparison = sum(
        trial["matcher_result"]["metrics"]["comparison_region_count"] for trial in trials
    )
    near = sum(trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials)
    return {
        "comparison_region_count": comparison,
        "complete_region_count": complete,
        "document_count": len(trials),
        "document_multiple_complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] > 1 for trial in trials
        ),
        "document_unique_structural_match_count": sum(
            trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
            for trial in trials
        ),
        "mapping_verified_count": 0,
        "near_region_count": near,
        "unresolved_document_count": len(trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-property scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_INVESTMENT_PROPERTY_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("investment-property scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("investment-property scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("investment-property scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("investment-property scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "ipfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("investment-property scan identity drifted")
    return canonical_clone_v1(value)


def build_investment_property_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    """Build the exact eight-document investment-property structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        pages, applied_count = support._matcher_pages(document, None)
        if applied_count != 0:
            raise _error("investment-property scan unexpectedly applied a semantic rescue")
        result = matcher.build_investment_property_variant_graph_document_v1(pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "FULL_DOCUMENT_INVESTMENT_PROPERTY_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "ipfdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_investment_property_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_investment_property_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("investment-property scan does not replay exactly")
    return supplied


def build_live_investment_property_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    return build_investment_property_full_document_scan_v1(semantic_index)


def validate_live_investment_property_full_document_scan_v1(
    value: Any, input_path: Path = DEFAULT_INPUT
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    return validate_investment_property_full_document_scan_replay_v1(value, semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_investment_property_full_document_scan_v1(args.input)
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
