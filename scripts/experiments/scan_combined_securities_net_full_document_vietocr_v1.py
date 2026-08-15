"""Scan all eight fresh-VietOCR PDFs for a combined securities net row."""

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
FORMAT_VERSION = "COMBINED_SECURITIES_NET_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "COMBINED_SECURITIES_NET_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_COMBINED_TRADING_AND_"
    "INVESTMENT_SECURITIES_NET_TWO_VALUE_ROW_SCAN_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "section_heading_retained_as_negative_control": True,
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


class CombinedSecuritiesNetFullDocumentScanV1Error(ValueError):
    """The semantic axis or combined-securities scan drifted."""


def _error(message: str) -> CombinedSecuritiesNetFullDocumentScanV1Error:
    return CombinedSecuritiesNetFullDocumentScanV1Error(message)


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


def _scan_support() -> ModuleType:
    return _load_module(
        "fx_gold_scan_support_for_combined_securities_net",
        "scan_fx_gold_activity_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "combined_securities_net_matcher_for_full_document_scan",
        "combined_securities_net_variant_graph_v1.py",
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
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "unresolved_document_count": len(trials) - unique,
        "wrapped_complete_region_count": sum(
            trial["matcher_result"]["metrics"]["wrapped_complete_region_count"] for trial in trials
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("combined-securities scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_COMBINED_SECURITIES_NET_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("combined-securities scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("combined-securities scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("combined-securities scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("combined-securities scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "csnfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("combined-securities scan identity drifted")
    return canonical_clone_v1(value)


def build_combined_securities_net_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    """Build the exact eight-document combined-securities structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    support = _scan_support()
    trials = []
    for document in axis["documents"]:
        result = matcher.build_combined_securities_net_variant_graph_document_v1(
            support._matcher_pages(document)
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
        "state": "FULL_DOCUMENT_COMBINED_SECURITIES_NET_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "csnfdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_combined_securities_net_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_combined_securities_net_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("combined-securities scan does not replay exactly")
    return supplied


def build_live_combined_securities_net_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _scan_support()._support()
    semantic_index = support._strict_json(support._stable_bytes(input_path), input_path.as_posix())
    return build_combined_securities_net_full_document_scan_v1(semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    result = build_live_combined_securities_net_full_document_scan_v1(args.input)
    sys.stdout.buffer.write(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
