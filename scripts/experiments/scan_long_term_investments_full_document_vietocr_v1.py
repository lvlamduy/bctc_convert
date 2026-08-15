"""Scan all eight fresh-VietOCR PDFs for other long-term investments."""

from __future__ import annotations

import argparse
import importlib.util
import json
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
FORMAT_VERSION = "LONG_TERM_INVESTMENTS_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
MATCHER_FORMAT = "LONG_TERM_INVESTMENTS_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_SHARED_LONG_TERM_INVESTMENT_"
    "OWNER_OPTIONAL_JOINT_VENTURE_ASSOCIATE_OTHER_ORGANIZATION_PROJECT_FUND_"
    "PROVISION_TOTAL_AND_NEXT_BOUNDARY_SCAN_ONLY_NO_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
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
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
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


class LongTermInvestmentsFullDocumentScanV1Error(ValueError):
    """The semantic axis or long-term-investment scan drifted."""


def _error(message: str) -> LongTermInvestmentsFullDocumentScanV1Error:
    return LongTermInvestmentsFullDocumentScanV1Error(message)


def _matcher() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/long_term_investments_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location("long_term_investments_matcher_for_scan", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load long-term-investment matcher: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _matcher_pages(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": line["bbox"],
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
            "primary_numeric_authority": page["primary_numeric_authority"],
        }
        for page in document["pages"]
    ]


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
        "unresolved_document_count": len(trials) - unique,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("long-term-investment scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_LONG_TERM_INVESTMENTS_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("long-term-investment scan identity or authority drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("long-term-investment scan trial fields drifted")
        result = trial["matcher_result"]
        if (
            trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(result) is not dict
            or result.get("format_version") != MATCHER_FORMAT
        ):
            raise _error("long-term-investment scan trial identity drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("long-term-investment scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "ltifdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("long-term-investment scan identity drifted")
    return canonical_clone_v1(value)


def build_long_term_investments_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    """Build the exact eight-document structural scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        result = matcher.build_long_term_investments_variant_graph_document_v1(
            _matcher_pages(document)
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
        "state": "FULL_DOCUMENT_LONG_TERM_INVESTMENTS_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "ltifdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_long_term_investments_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_long_term_investments_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("long-term-investment scan does not replay exactly")
    return supplied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    semantic_index = json.loads((PROJECT_ROOT / args.input).read_text(encoding="utf-8"))
    result = build_long_term_investments_full_document_scan_v1(semantic_index)
    payload = canonical_json_bytes_v1(result) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    main()
