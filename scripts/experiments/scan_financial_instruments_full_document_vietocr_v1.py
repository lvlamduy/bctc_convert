"""Scan all eight fresh-VietOCR PDFs for carrying/fair-value tables."""

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
FORMAT_VERSION = "FINANCIAL_INSTRUMENTS_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "FINANCIAL_INSTRUMENTS_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_PDF_BANK_BLIND_FINANCIAL_INSTRUMENTS_"
    "CARRYING_FAIR_VALUE_SCAN_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bounded_detailed_table_absence_only": True,
    "complete_pdf_scanned_for_every_document": True,
    "interest_currency_and_liquidity_risk_controls_retained": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "persisted_result_self_authenticating": False,
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


class FinancialInstrumentsFullDocumentScanV1Error(ValueError):
    """The semantic axis or financial-instruments scan drifted."""


def _error(message: str) -> FinancialInstrumentsFullDocumentScanV1Error:
    return FinancialInstrumentsFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load financial-instruments support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _support() -> ModuleType:
    return _load(
        "fx_gold_scan_support_for_financial_instruments",
        "scan_fx_gold_activity_full_document_vietocr_v1.py",
    )


def _matcher() -> ModuleType:
    return _load(
        "financial_instruments_matcher_for_scan",
        "financial_instruments_variant_graph_v1.py",
    )


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(t["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for t in trials)
    return {
        "bounded_detailed_table_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            t["matcher_result"]["metrics"]["complete_region_count"] for t in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            t["matcher_result"]["metrics"]["near_region_count"] for t in trials
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("financial-instruments scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_FINANCIAL_INSTRUMENTS_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("financial-instruments scan identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial)
            != {"document_ordinal", "document_provenance", "matcher_result", "source_pdf_sha256"}
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("financial-instruments trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "fifdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("financial-instruments scan ID drifted")
    return canonical_clone_v1(value)


def build_financial_instruments_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    matcher = _matcher()
    support = _support()
    trials = []
    for document in axis["documents"]:
        result = matcher.build_financial_instruments_variant_graph_document_v1(
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
        "state": "FULL_DOCUMENT_FINANCIAL_INSTRUMENTS_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate({**material, "scan_id": "fifdsv1:scan:" + canonical_json_sha256_v1(material)})


def validate_financial_instruments_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_financial_instruments_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("financial-instruments scan does not replay exactly")
    return supplied


def build_live_financial_instruments_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    support = _support()._support()
    semantic_index = support._strict_json(support._stable_bytes(input_path), input_path.as_posix())
    return build_financial_instruments_full_document_scan_v1(semantic_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(build_live_financial_instruments_full_document_scan_v1(args.input))
    )


if __name__ == "__main__":
    main()
