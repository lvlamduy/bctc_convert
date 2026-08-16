"""Scan all eight fresh-VietOCR PDFs for interest-rate-risk tables."""

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
FORMAT_VERSION = "INTEREST_RATE_RISK_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "INTEREST_RATE_RISK_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_INTEREST_RATE_RISK_"
    "OPTIONAL_REPRICING_AXIS_ASSET_LIABILITY_GAP_AND_GEOMETRY_SELECTED_"
    "ROTATED_SAME_TRANSFORMER_RESCUE_SCAN_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bounded_detailed_table_absence_only": True,
    "complete_pdf_scanned_for_every_document": True,
    "currency_liquidity_and_fair_value_controls_retained": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_selected_by_geometry_not_bank_or_page": True,
    "rotated_rescue_uses_same_pinned_vietocr_transformer": True,
}
_FIELDS = {
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


class InterestRateRiskFullDocumentScanV1Error(ValueError):
    """The semantic axis or interest-rate-risk scan drifted."""


def _error(message: str) -> InterestRateRiskFullDocumentScanV1Error:
    return InterestRateRiskFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load interest-rate-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _support() -> ModuleType:
    return _load(
        "rotated_scan_support_for_interest_rate_risk",
        "scan_capital_and_funds_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load(
        "interest_rate_risk_matcher_for_scan",
        "interest_rate_risk_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "bounded_detailed_table_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "complete_table_page_count": sum(
            trial["matcher_result"]["metrics"]["complete_table_page_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("interest-rate-risk scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_INTEREST_RATE_RISK_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("interest-rate-risk scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial)
            != {
                "document_ordinal",
                "document_provenance",
                "matcher_result",
                "rotated_rescue_line_count",
                "source_pdf_sha256",
            }
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or type(trial["rotated_rescue_line_count"]) is not int
        ):
            raise _error("interest-rate-risk trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "irrfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("interest-rate-risk scan ID drifted")
    return canonical_clone_v1(value)


def build_interest_rate_risk_full_document_scan_v1(
    semantic_index: Any, rescue: Any
) -> dict[str, Any]:
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    authenticated_rescue = support._validate_rescue(rescue)
    rescue_by_locator = {
        (
            sample["document_ordinal"],
            sample["physical_page"],
            sample["source_line_index"],
        ): sample
        for sample in authenticated_rescue["samples"]
    }
    trials = []
    total_applied = 0
    for document in axis["documents"]:
        pages, applied_count = support._matcher_pages(document, rescue_by_locator)
        total_applied += applied_count
        result = matcher.build_interest_rate_risk_variant_graph_document_v1(pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": result,
                "rotated_rescue_line_count": applied_count,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if total_applied != authenticated_rescue["metrics"]["line_count"]:
        raise _error("rotated semantic rescue did not join its exact source-line denominator")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_rescue": {
            "input_refs": authenticated_rescue["input_refs"],
            "metrics": authenticated_rescue["metrics"],
            "projection_id": authenticated_rescue["projection_id"],
        },
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "FULL_DOCUMENT_INTEREST_RATE_RISK_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate({**material, "scan_id": "irrfdsv1:scan:" + canonical_json_sha256_v1(material)})


def validate_interest_rate_risk_full_document_scan_replay_v1(
    value: Any, semantic_index: Any, rescue: Any
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_interest_rate_risk_full_document_scan_v1(semantic_index, rescue)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("interest-rate-risk scan does not replay exactly")
    return supplied


def build_live_interest_rate_risk_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._support()._fixed_json(input_path)
    rescue = support._rescue_builder().read_verified_full_document_rotated_vietocr_rescue_v1()
    return build_interest_rate_risk_full_document_scan_v1(semantic_index, rescue)


def validate_live_interest_rate_risk_full_document_scan_v1(
    value: Any, input_path: Path = DEFAULT_INPUT
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._support()._fixed_json(input_path)
    rescue = support._rescue_builder().read_verified_full_document_rotated_vietocr_rescue_v1()
    return validate_interest_rate_risk_full_document_scan_replay_v1(value, semantic_index, rescue)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(build_live_interest_rate_risk_full_document_scan_v1(args.input))
    )


if __name__ == "__main__":
    main()
