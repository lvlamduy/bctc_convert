"""Run the bank-blind maturity variant graph over eight complete VietOCR PDFs.

The upstream semantic index must contain every line from every page in the
fixed eight-document panel and must identify fresh VietOCR VGG Transformer as
its sole semantic text source.  This adapter adds no bank-specific rule: bank
codes remain output provenance, while each document is reduced to the same
page/line contract and scanned exactly once by the common variant matcher.

The full-document semantic index deliberately has no numeric authority.
Consequently this scan can establish a unique structural candidate but cannot
promote numeric, mapping, canonical, or export authority.
"""

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
    FullDocumentVietOCRAccountingAxisV1Error,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_MATURITY_8DOCUMENT_FULL_VIETOCR_STRUCTURE_SCAN_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_WHOLE_DOCUMENT_UNIQUE_VARIANT_STRUCTURE_SCAN_ONLY_"
    "NO_SOURCE_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
EXPECTED_BANK_ORDER = EXPECTED_DOCUMENT_ORDER
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "canonical_or_export_authority": False,
    "exact_input_replay_required": True,
    "full_document_uniqueness_evaluated": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "schema_candidate_is_verified_mapping": False,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}


class LoanMaturityFullDocumentScanV1Error(ValueError):
    """The full-document semantic index or deterministic scan drifted."""


def _error(message: str) -> LoanMaturityFullDocumentScanV1Error:
    return LoanMaturityFullDocumentScanV1Error(message)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _matcher() -> ModuleType:
    return _load_module(
        PROJECT_ROOT / "scripts/experiments/loan_maturity_variant_graph_v1.py",
        "loan_maturity_variant_graph_v1_for_full_document_scan",
    )


def _source_sha256(value: Any) -> str:
    if type(value) is not dict or type(value.get("sha256")) is not str:
        raise _error("source PDF content reference drifted")
    sha256 = value["sha256"]
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise _error("source PDF SHA-256 drifted")
    return sha256


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def build_loan_maturity_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    """Build one deterministic eight-document structure-only scan."""

    try:
        axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    except FullDocumentVietOCRAccountingAxisV1Error as error:
        raise _error(str(error)) from error
    matcher = _matcher()
    trials: list[dict[str, Any]] = []
    for document in axis["documents"]:
        document_pages: list[dict[str, Any]] = []
        semantic_pages: list[dict[str, Any]] = []
        for page in document["pages"]:
            document_pages.append(
                {
                    "page_sequence": page["page_sequence"],
                    "lines": [
                        {
                            "qwen35_challenger_text": None,
                            "source_line_index": line["source_line_index"],
                            "vietocr_text": line["vietocr_text"],
                        }
                        for line in page["lines"]
                    ],
                }
            )
            semantic_pages.append(
                {
                    "page_sequence": page["page_sequence"],
                    "primary_numeric_authority": False,
                    "lines": [
                        {
                            "bbox": line["bbox"],
                            "qwen35_challenger_text": None,
                            "source_line_index": line["source_line_index"],
                            "source_text": None,
                            "vietocr_text": line["vietocr_text"],
                        }
                        for line in page["lines"]
                    ],
                }
            )
        region_scan = matcher.build_loan_maturity_region_scan_v1(document_pages)
        match = matcher.scan_loan_maturity_variant_graph_document_v1(document_pages, semantic_pages)
        trials.append(
            {
                "bank_provenance": document["document_provenance"],
                "document_ordinal": document["document_ordinal"],
                "matcher_result": match,
                "region_scan": region_scan,
                "source_pdf_sha256": _source_sha256(document["source_pdf"]),
            }
        )

    structure_resolved = sum(
        trial["matcher_result"]["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        for trial in trials
    )
    candidate_count = sum(trial["matcher_result"]["document_candidate_count"] for trial in trials)
    complete_region_count = sum(
        trial["region_scan"]["metrics"]["complete_context_region_count"] for trial in trials
    )
    near_region_count = sum(
        trial["region_scan"]["metrics"]["near_region_count"] for trial in trials
    )
    ordered_region_count = sum(
        trial["region_scan"]["metrics"]["ordered_anchor_region_count"] for trial in trials
    )
    metrics = {
        "accepted_numeric_graph_count": 0,
        "complete_context_region_count": complete_region_count,
        "document_count": len(trials),
        "document_multiple_complete_context_region_count": sum(
            trial["region_scan"]["metrics"]["complete_context_region_count"] > 1 for trial in trials
        ),
        "document_unique_candidate_count": sum(
            trial["matcher_result"]["document_candidate_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": 0,
        "near_region_count": near_region_count,
        "ordered_anchor_region_count": ordered_region_count,
        "structure_resolved_numeric_unresolved_count": structure_resolved,
        "total_document_candidate_count": candidate_count,
        "unresolved_document_count": len(trials) - structure_resolved,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_semantic_axis_sha256": _sha256(axis["semantic_axis_sha256"], "semantic text axis"),
        "metrics": metrics,
        "state": "FULL_DOCUMENT_STRUCTURE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "scan_id": "lmfdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("full-document structure scan result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_STRUCTURE_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_BANK_ORDER)
        or type(value["metrics"]) is not dict
    ):
        raise _error("full-document structure scan identity/authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "lmfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("full-document structure scan identity drifted")
    _sha256(value["input_semantic_axis_sha256"], "scan input semantic axis")
    trials = value["trials"]
    candidate_count = 0
    resolved_count = 0
    for ordinal, (trial, expected_bank) in enumerate(
        zip(trials, EXPECTED_BANK_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "bank_provenance",
            "document_ordinal",
            "matcher_result",
            "region_scan",
            "source_pdf_sha256",
        }:
            raise _error("full-document structure scan trial fields drifted")
        matcher_result = trial["matcher_result"]
        if (
            trial["bank_provenance"] != expected_bank
            or trial["document_ordinal"] != ordinal
            or type(matcher_result) is not dict
            or matcher_result.get("format_version") != "LOAN_MATURITY_VARIANT_GRAPH_V1"
            or matcher_result.get("status")
            not in {
                "ACCEPTED_VARIANT_GRAPH",
                "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED",
                "UNRESOLVED",
            }
            or type(matcher_result.get("document_candidate_count")) is not int
            or matcher_result["document_candidate_count"] < 0
        ):
            raise _error("full-document structure scan trial identity/status drifted")
        region_scan = trial["region_scan"]
        if (
            type(region_scan) is not dict
            or region_scan.get("format_version") != "ACCOUNTING_VARIANT_GRAPH_ENGINE_REGION_SCAN_V1"
            or region_scan.get("family_id") != "LOAN_MATURITY_BUCKETS"
            or type(region_scan.get("regions")) is not list
            or type(region_scan.get("near_regions")) is not list
            or type(region_scan.get("metrics")) is not dict
        ):
            raise _error("full-document generic region scan identity drifted")
        engine_candidate_count = sum(
            not any(
                reason != "OWNER_CONTEXT_NOT_RESOLVED"
                for reason in region.get("unresolved_reasons", [])
            )
            for region in region_scan["regions"]
        )
        if engine_candidate_count != matcher_result["document_candidate_count"]:
            raise _error("generic region and maturity candidate denominators disagree")
        _sha256(trial["source_pdf_sha256"], "trial source PDF")
        candidate_count += matcher_result["document_candidate_count"]
        resolved_count += matcher_result["status"] == ("ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED")
    complete_region_count = sum(
        trial["region_scan"]["metrics"]["complete_context_region_count"] for trial in trials
    )
    near_region_count = sum(
        trial["region_scan"]["metrics"]["near_region_count"] for trial in trials
    )
    ordered_region_count = sum(
        trial["region_scan"]["metrics"]["ordered_anchor_region_count"] for trial in trials
    )
    expected_metrics = {
        "accepted_numeric_graph_count": 0,
        "complete_context_region_count": complete_region_count,
        "document_count": len(EXPECTED_BANK_ORDER),
        "document_multiple_complete_context_region_count": sum(
            trial["region_scan"]["metrics"]["complete_context_region_count"] > 1 for trial in trials
        ),
        "document_unique_candidate_count": sum(
            trial["matcher_result"]["document_candidate_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": 0,
        "near_region_count": near_region_count,
        "ordered_anchor_region_count": ordered_region_count,
        "structure_resolved_numeric_unresolved_count": resolved_count,
        "total_document_candidate_count": candidate_count,
        "unresolved_document_count": len(EXPECTED_BANK_ORDER) - resolved_count,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("full-document structure scan metrics drifted")
    return canonical_clone_v1(value)


def validate_loan_maturity_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    """Exact-rebuild a scan from the verified full-document index."""

    persisted = _validate_result(value)
    rebuilt = build_loan_maturity_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("full-document structure scan does not replay exactly")
    return rebuilt


def build_live_loan_maturity_full_document_scan_v1(
    input_path: Path | None = None,
) -> dict[str, Any]:
    """Replay the fixed upstream VietOCR index and scan all eight PDFs."""

    if input_path is None:
        builder = _load_module(
            PROJECT_ROOT
            / "scripts/experiments/build_loan_maturity_full_document_vietocr_request_v1.py",
            "full_document_vietocr_builder_for_structure_scan",
        )
        index = builder.read_verified_vietocr_proposals_v1()
    else:
        path = input_path if input_path.is_absolute() else PROJECT_ROOT / input_path
        try:
            index = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _error(f"cannot load explicit semantic index: {path}") from error
    return build_loan_maturity_full_document_scan_v1(index)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan eight full VietOCR PDFs for maturity graphs")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_live_loan_maturity_full_document_scan_v1(args.input)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(raw)
    else:
        output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
        if output.exists():
            raise _error(f"refusing to overwrite scan output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
