"""Scan eight complete fresh-VietOCR PDFs for subsidiary transactions."""

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
FORMAT_VERSION = "SUBSIDIARY_ACQUISITION_DISPOSAL_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "SUBSIDIARY_ACQUISITION_DISPOSAL_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_SUBSIDIARY_"
    "ACQUISITION_DISPOSAL_CASH_FLOW_DETAIL_SCAN_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_identity_used_for_matching_or_routing": False,
    "bounded_detailed_note_absence_only": True,
    "canonical_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
    "policy_and_cash_flow_controls_retained": True,
    "public_exact_replay_required": True,
}
_FIELDS = {
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


class SubsidiaryAcquisitionDisposalFullDocumentScanV1Error(ValueError):
    """The semantic axis or subsidiary-transaction scan drifted."""


def _error(message: str) -> SubsidiaryAcquisitionDisposalFullDocumentScanV1Error:
    return SubsidiaryAcquisitionDisposalFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load subsidiary-transaction support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _support() -> ModuleType:
    return _load(
        "fx_gold_scan_support_for_subsidiary_transactions",
        "scan_fx_gold_activity_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load(
        "subsidiary_transaction_matcher_for_scan",
        "subsidiary_acquisition_disposal_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "bounded_detailed_note_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("subsidiary-transaction scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_SUBSIDIARY_TRANSACTION_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("subsidiary-transaction scan identity drifted")
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
                "source_pdf_sha256",
            }
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("subsidiary-transaction trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "sadfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("subsidiary-transaction scan ID drifted")
    return canonical_clone_v1(value)


def build_subsidiary_acquisition_disposal_full_document_scan_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    support = _support()
    matcher = _matcher()
    trials = []
    for document in axis["documents"]:
        result = matcher.build_subsidiary_acquisition_disposal_variant_graph_document_v1(
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
        "state": "FULL_DOCUMENT_SUBSIDIARY_TRANSACTION_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate({**material, "scan_id": "sadfdsv1:scan:" + canonical_json_sha256_v1(material)})


def validate_subsidiary_acquisition_disposal_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_subsidiary_acquisition_disposal_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("subsidiary-transaction scan does not replay exactly")
    return supplied


def build_live_subsidiary_acquisition_disposal_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()._support()
    semantic_index = support._strict_json(support._stable_bytes(input_path), input_path.as_posix())
    return build_subsidiary_acquisition_disposal_full_document_scan_v1(semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(
            build_live_subsidiary_acquisition_disposal_full_document_scan_v1(args.input)
        )
    )


if __name__ == "__main__":
    main()
