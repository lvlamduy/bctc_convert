"""Scan all eight fresh-VietOCR PDFs for investment-securities sale activity."""

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
FORMAT_VERSION = "INVESTMENT_SECURITIES_ACTIVITY_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "SECURITIES_SALE_ACTIVITY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_VARIANT = "INVESTMENT_SECURITIES"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_INVESTMENT_SECURITIES_"
    "SALE_NET_OWNER_REQUIRED_INCOME_EXPENSE_OPTIONAL_PROVISION_OR_OTHER_"
    "FLEXIBLE_WRAP_ORDER_AND_DOCUMENT_SECTION_UNIT_INHERITANCE_SCAN_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "trading_securities_regions_retained_as_distinct_controls": True,
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


class InvestmentSecuritiesActivityFullDocumentScanV1Error(ValueError):
    """The semantic axis or investment-securities scan drifted."""


def _error(message: str) -> InvestmentSecuritiesActivityFullDocumentScanV1Error:
    return InvestmentSecuritiesActivityFullDocumentScanV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load scan support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _trading_scan_support() -> ModuleType:
    return _load_module(
        "trading_scan_support_for_investment_securities_activity",
        "scan_trading_securities_activity_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "securities_sale_matcher_for_investment_full_document_scan",
        "securities_sale_activity_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "inherited_document_unit_region_count": sum(
            region["layout"]["inherited_document_unit_used"]
            for trial in trials
            for region in trial["matcher_result"]["regions"]
        ),
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "optional_other_child_region_count": sum(
            "OTHER" in region["layout"]["child_roles"]
            for trial in trials
            for region in trial["matcher_result"]["regions"]
        ),
        "provision_child_region_count": sum(
            trial["matcher_result"]["metrics"]["provision_child_region_count"] for trial in trials
        ),
        "unresolved_document_count": len(trials) - unique,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-securities scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_INVESTMENT_SECURITIES_ACTIVITY_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("investment-securities scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("investment-securities scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or trial["matcher_result"].get("family_variant") != FAMILY_VARIANT
        ):
            raise _error("investment-securities scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("investment-securities scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "isafdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("investment-securities scan identity drifted")
    return canonical_clone_v1(value)


def build_investment_securities_activity_full_document_scan_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    """Build the exact eight-document investment-securities structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    support = _trading_scan_support()._scan_support()
    trials = []
    for document in axis["documents"]:
        result = matcher.build_securities_sale_activity_variant_graph_document_v1(
            support._matcher_pages(document), family_variant=FAMILY_VARIANT
        )
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
        "state": "FULL_DOCUMENT_INVESTMENT_SECURITIES_ACTIVITY_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "isafdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_investment_securities_activity_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_investment_securities_activity_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("investment-securities scan does not replay exactly")
    return supplied


def build_live_investment_securities_activity_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _trading_scan_support()._scan_support()._support()
    semantic_index = support._strict_json(support._stable_bytes(input_path), input_path.as_posix())
    return build_investment_securities_activity_full_document_scan_v1(semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    result = build_live_investment_securities_activity_full_document_scan_v1(args.input)
    sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
