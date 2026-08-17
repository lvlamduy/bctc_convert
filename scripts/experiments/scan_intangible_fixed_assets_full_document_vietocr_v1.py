"""Scan all eight fresh-VietOCR PDFs for intangible fixed-asset movements."""

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
FORMAT_VERSION = "INTANGIBLE_FIXED_ASSETS_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "INTANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
MATCHER_VARIANT_PROFILE = "CURRENT_V1"
_MATCHER_FORMAT_BY_PROFILE = {
    "CURRENT_V1": MATCHER_FORMAT,
    "REPORTING_PERIOD_GENERAL_V2": "INTANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V2",
}
SCAN_ID_PREFIX = "ifafdsv1:scan:"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_SHARED_FIXED_ASSET_ENGINE_"
    "INTANGIBLE_OWNER_COST_ACCUMULATED_AMORTIZATION_CARRYING_VALUE_OPTIONAL_"
    "MOVEMENTS_ASSET_CLASS_COLUMNS_AND_CURRENT_COMPARATIVE_PERIOD_CANDIDATES_"
    "SCAN_ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "current_and_comparative_complete_regions_retained_for_period_adjudication": True,
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
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}


class IntangibleFixedAssetsFullDocumentScanV1Error(ValueError):
    """The semantic axis or intangible-fixed-assets scan drifted."""


def _error(message: str) -> IntangibleFixedAssetsFullDocumentScanV1Error:
    return IntangibleFixedAssetsFullDocumentScanV1Error(message)


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
        "tangible_fixed_assets_scan_support_for_intangible_assets",
        "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "shared_fixed_assets_matcher_for_intangible_assets",
        "tangible_fixed_assets_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    complete = sum(trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials)
    near = sum(trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials)
    metrics = {
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
    if MATCHER_VARIANT_PROFILE != "CURRENT_V1":
        metrics["rotated_rescue_line_count"] = sum(
            trial["rotated_rescue_line_count"] for trial in trials
        )
    return metrics


def _validate_result(value: Any) -> dict[str, Any]:
    expected_result_fields = set(_RESULT_FIELDS)
    if MATCHER_VARIANT_PROFILE != "CURRENT_V1":
        expected_result_fields.add("input_rescue")
    if type(value) is not dict or set(value) != expected_result_fields:
        raise _error("intangible-fixed-assets scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_INTANGIBLE_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("intangible-fixed-assets scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        expected_trial_fields = {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }
        if MATCHER_VARIANT_PROFILE != "CURRENT_V1":
            expected_trial_fields.add("rotated_rescue_line_count")
        if type(trial) is not dict or set(trial) != expected_trial_fields:
            raise _error("intangible-fixed-assets scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version")
            != _MATCHER_FORMAT_BY_PROFILE.get(MATCHER_VARIANT_PROFILE)
        ):
            raise _error("intangible-fixed-assets scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("intangible-fixed-assets scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != SCAN_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("intangible-fixed-assets scan identity drifted")
    return canonical_clone_v1(value)


def build_intangible_fixed_assets_full_document_scan_v1(
    semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the exact eight-document intangible-assets structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    full_rescue_by_locator = (
        support._full_rescue_by_locator(rescue, axis["semantic_axis_sha256"])
        if rescue is not None
        and rescue.get("format_version") == support.FULL_DOCUMENT_RESCUE_FORMAT
        else None
    )
    trials = []
    for document in axis["documents"]:
        pages, applied_count = support._matcher_pages(document, rescue, full_rescue_by_locator)
        result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
            pages, variant_profile=MATCHER_VARIANT_PROFILE
        )
        trial = {
            "document_ordinal": document["document_ordinal"],
            "document_provenance": document["document_provenance"],
            "matcher_result": result,
            "source_pdf_sha256": document["source_pdf"]["sha256"],
        }
        if MATCHER_VARIANT_PROFILE != "CURRENT_V1":
            trial["rotated_rescue_line_count"] = applied_count
        elif applied_count != 0:
            raise _error("current-profile intangible scan unexpectedly applied a rescue")
        trials.append(trial)
    if full_rescue_by_locator is not None and sum(
        trial["rotated_rescue_line_count"] for trial in trials
    ) != len(full_rescue_by_locator):
        raise _error("full-document rotated rescue denominator was not consumed exactly once")
    rescue_ref = None
    if rescue is not None and rescue.get("format_version") == support.RESCUE_FORMAT:
        rescue_ref = {
            "input_refs": canonical_clone_v1(rescue["input_refs"]),
            "line_count": rescue["line_count"],
            "rescue_id": rescue["rescue_id"],
            "source_pdf_sha256": rescue["source_pdf_sha256"],
            "source_projection_sha256": rescue["source_projection_sha256"],
        }
    elif full_rescue_by_locator is not None:
        rescue_ref = {
            "input_refs": canonical_clone_v1(rescue["input_refs"]),
            "line_count": len(full_rescue_by_locator),
            "projection_id": rescue["projection_id"],
            "source_semantic_axis_sha256": rescue["source_semantic_axis_sha256"],
        }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "FULL_DOCUMENT_INTANGIBLE_FIXED_ASSETS_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    if MATCHER_VARIANT_PROFILE != "CURRENT_V1":
        material["input_rescue"] = rescue_ref
    return _validate_result(
        {**material, "scan_id": SCAN_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_intangible_fixed_assets_full_document_scan_replay_v1(
    value: Any, semantic_index: Any, rescue: dict[str, Any] | None = None
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_intangible_fixed_assets_full_document_scan_v1(semantic_index, rescue)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("intangible-fixed-assets scan does not replay exactly")
    return supplied


def build_live_intangible_fixed_assets_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
    rescue_root: Path = Path("output/development/vib-page37-rotated-vietocr-v1"),
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = (
        None
        if MATCHER_VARIANT_PROFILE == "CURRENT_V1"
        else support._profile_rescue(semantic_index, rescue_root)
    )
    return build_intangible_fixed_assets_full_document_scan_v1(semantic_index, rescue)


def validate_live_intangible_fixed_assets_full_document_scan_v1(
    value: Any,
    input_path: Path = DEFAULT_INPUT,
    rescue_root: Path = Path("output/development/vib-page37-rotated-vietocr-v1"),
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    rescue = (
        None
        if MATCHER_VARIANT_PROFILE == "CURRENT_V1"
        else support._profile_rescue(semantic_index, rescue_root)
    )
    return validate_intangible_fixed_assets_full_document_scan_replay_v1(
        value, semantic_index, rescue
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_intangible_fixed_assets_full_document_scan_v1(args.input)
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
