"""Scan all eight fresh-VietOCR PDFs for other-payables disclosures."""

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
FORMAT_VERSION = "OTHER_PAYABLES_LIABILITIES_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "OTHER_PAYABLES_LIABILITIES_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_OTHER_PAYABLES_OWNER_"
    "INTERNAL_EXTERNAL_OPTIONAL_CHILD_PERIOD_UNIT_SCAN_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
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


class OtherPayablesLiabilitiesFullDocumentScanV1Error(ValueError):
    """The semantic axis or other-payables scan drifted."""


def _error(message: str) -> OtherPayablesLiabilitiesFullDocumentScanV1Error:
    return OtherPayablesLiabilitiesFullDocumentScanV1Error(message)


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
        "tangible_fixed_assets_support_for_other_payables",
        "scan_tangible_fixed_assets_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load_module(
        "other_payables_matcher_for_full_document_scan",
        "other_payables_liabilities_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    complete = sum(trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials)
    near = sum(trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials)
    return {
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
        raise _error("other-payables scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_OTHER_PAYABLES_LIABILITIES_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("other-payables scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("other-payables scan trial fields drifted")
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("other-payables scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("other-payables scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "oplifdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("other-payables scan identity drifted")
    return canonical_clone_v1(value)


def build_other_payables_liabilities_full_document_scan_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    """Build the exact eight-document other-payables structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        pages, applied_count = support._matcher_pages(document, None)
        if applied_count != 0:
            raise _error("other-payables scan unexpectedly applied a semantic rescue")
        result = matcher.build_other_payables_liabilities_variant_graph_document_v1(pages)
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
        "state": "FULL_DOCUMENT_OTHER_PAYABLES_LIABILITIES_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "oplifdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_other_payables_liabilities_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_other_payables_liabilities_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-payables scan does not replay exactly")
    return supplied


def build_live_other_payables_liabilities_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    return build_other_payables_liabilities_full_document_scan_v1(semantic_index)


def validate_live_other_payables_liabilities_full_document_scan_v1(
    value: Any, input_path: Path = DEFAULT_INPUT
) -> dict[str, Any]:
    support = _support()
    semantic_index, _ = support._fixed_json(input_path)
    return validate_other_payables_liabilities_full_document_scan_replay_v1(value, semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_other_payables_liabilities_full_document_scan_v1(args.input)
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
