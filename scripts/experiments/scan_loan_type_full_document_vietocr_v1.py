"""Run the bank-blind loan-type graph over all eight fresh VietOCR PDFs."""

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
FORMAT_VERSION = "LOAN_TYPE_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_LOAN_TYPE_VARIANT_STRUCTURE_SCAN_ONLY_"
    "NO_SOURCE_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
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


class LoanTypeFullDocumentScanV1Error(ValueError):
    """The shared semantic axis, family result, or replay drifted."""


def _error(message: str) -> LoanTypeFullDocumentScanV1Error:
    return LoanTypeFullDocumentScanV1Error(message)


def _matcher() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/loan_type_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location(
        "loan_type_variant_graph_v1_for_full_document_scan", path
    )
    if spec is None or spec.loader is None:
        raise _error(f"cannot load loan-type matcher: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-type full-document scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_LOAN_TYPE_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("loan-type full-document scan identity/authority drifted")
    _sha256(value["input_semantic_axis_sha256"], "scan semantic axis")
    if type(value["input_axis_projection_id"]) is not str or not value[
        "input_axis_projection_id"
    ].startswith("fdvaav1:projection:"):
        raise _error("scan accounting-axis projection identity drifted")

    unique_count = 0
    structural_count = 0
    near_count = 0
    region_count = 0
    semantic_corroborated_lane_count = 0
    for ordinal, (trial, expected_code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "document_ordinal",
            "document_provenance",
            "matcher_result",
            "source_pdf_sha256",
        }:
            raise _error("loan-type full-document trial fields drifted")
        result = trial["matcher_result"]
        if (
            trial["document_provenance"] != expected_code
            or type(trial["document_ordinal"]) is not int
            or trial["document_ordinal"] != ordinal
            or type(result) is not dict
            or result.get("format_version") != "LOAN_TYPE_VARIANT_GRAPH_DOCUMENT_V1"
            or result.get("status")
            not in {
                "ACCEPTED_UNIQUE_VARIANT_GRAPH",
                "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS",
                "UNRESOLVED_NO_COMPLETE_REGION",
            }
        ):
            raise _error("loan-type full-document trial identity/status drifted")
        _sha256(trial["source_pdf_sha256"], "trial source PDF")
        result_metrics = result.get("metrics")
        uniqueness = result.get("uniqueness")
        if type(result_metrics) is not dict or type(uniqueness) is not dict:
            raise _error("loan-type matcher metrics/uniqueness drifted")
        unique_count += uniqueness.get("status") == "UNIQUE_FULL_MATCH"
        structural_count += result_metrics.get("structurally_resolved_graph_count", 0)
        near_count += result_metrics.get("near_region_count", 0)
        region_count += result_metrics.get("complete_owner_table_region_count", 0)
        semantic_corroborated_lane_count += result_metrics.get(
            "semantic_accounting_corroborated_lane_count", 0
        )

    expected_metrics = {
        "accepted_numeric_graph_count": 0,
        "document_count": len(EXPECTED_DOCUMENT_ORDER),
        "document_unique_structural_match_count": unique_count,
        "mapping_verified_count": 0,
        "near_region_count": near_count,
        "owner_table_region_count": region_count,
        "semantic_proposal_accounting_corroborated_lane_count": (semantic_corroborated_lane_count),
        "structure_resolved_numeric_unresolved_count": structural_count,
        "unresolved_document_count": len(EXPECTED_DOCUMENT_ORDER) - unique_count,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("loan-type full-document scan metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "ltfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("loan-type full-document scan identity drifted")
    return canonical_clone_v1(value)


def build_loan_type_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    """Build the deterministic eight-document structure-only loan-type scan."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    trials: list[dict[str, Any]] = []
    for document in axis["documents"]:
        matcher_pages = [
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
        match = matcher.build_loan_type_variant_graph_document_v1(matcher_pages)
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": match,
                "source_pdf_sha256": _sha256(document["source_pdf"]["sha256"], "source PDF"),
            }
        )
    unique_count = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    metrics = {
        "accepted_numeric_graph_count": 0,
        "document_count": len(trials),
        "document_unique_structural_match_count": unique_count,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "owner_table_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_owner_table_region_count"]
            for trial in trials
        ),
        "semantic_proposal_accounting_corroborated_lane_count": sum(
            trial["matcher_result"]["metrics"]["semantic_accounting_corroborated_lane_count"]
            for trial in trials
        ),
        "structure_resolved_numeric_unresolved_count": sum(
            trial["matcher_result"]["metrics"]["structurally_resolved_graph_count"]
            for trial in trials
        ),
        "unresolved_document_count": len(trials) - unique_count,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": metrics,
        "state": "FULL_DOCUMENT_LOAN_TYPE_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "ltfdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_type_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    """Exact-rebuild the scan from the fixed fresh semantic index."""

    persisted = _validate_result(value)
    rebuilt = build_loan_type_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-type full-document scan does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    semantic_index = json.loads(args.input.read_text(encoding="utf-8"))
    result = build_loan_type_full_document_scan_v1(semantic_index)
    raw = canonical_json_bytes_v1(result) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(raw)
    else:
        if args.output.exists():
            raise _error(f"refusing to overwrite scan output: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
