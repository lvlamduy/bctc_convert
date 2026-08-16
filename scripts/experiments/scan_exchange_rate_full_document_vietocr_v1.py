"""Replay all eight full PDFs through the bank-blind exchange-rate matcher."""

from __future__ import annotations

import argparse
import hashlib
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
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
FORMAT_VERSION = "EXCHANGE_RATE_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "EXCHANGE_RATE_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "FRESH_VIETOCR_TRANSFORMER_COMPLETE_EIGHT_PDF_BANK_BLIND_EXCHANGE_RATE_"
    "OWNER_PERIOD_UNIT_CURRENCY_ROW_GEOMETRY_SCAN_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bounded_table_absence_only": True,
    "complete_pdf_scanned_for_every_document": True,
    "mapping_verified_count": 0,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_first_variant_graph_used": True,
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


class ExchangeRateFullDocumentScanV1Error(ValueError):
    """The full-document exchange-rate scan drifted."""


def _error(message: str) -> ExchangeRateFullDocumentScanV1Error:
    return ExchangeRateFullDocumentScanV1Error(message)


def _load_matcher() -> ModuleType:
    name = "exchange_rate_variant_graph_for_full_document_scan"
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments/exchange_rate_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load exchange-rate matcher: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        item["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for item in trials
    )
    return {
        "bounded_table_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            item["matcher_result"]["metrics"]["complete_region_count"] for item in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            item["matcher_result"]["metrics"]["near_region_count"] for item in trials
        ),
        "source_row_count": sum(
            item["matcher_result"]["metrics"]["complete_source_row_count"] for item in trials
        ),
        "supported_schema_row_count": sum(
            item["matcher_result"]["metrics"]["supported_schema_row_count"] for item in trials
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("exchange-rate scan fields drifted")
    trials = value["trials"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_DOCUMENT_EXCHANGE_RATE_SCAN_COMPLETE"
        or value["input_semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(trials) is not list
        or len(trials) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(trials))
    ):
        raise _error("exchange-rate scan identity drifted")
    for ordinal, (trial, code) in enumerate(zip(trials, EXPECTED_DOCUMENT_ORDER, strict=True), 1):
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
            or type(trial["source_pdf_sha256"]) is not str
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
        ):
            raise _error("exchange-rate scan trial axis drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "erfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("exchange-rate scan ID drifted")
    return canonical_clone_v1(value)


def build_exchange_rate_full_document_scan_v1(semantic_index: Any) -> dict[str, Any]:
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256:
        raise _error("exchange-rate semantic axis drifted")
    matcher = _load_matcher()
    trials = []
    for document in axis["documents"]:
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": matcher.build_exchange_rate_variant_graph_document_v1(
                    document["pages"]
                ),
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
        "state": "FULL_DOCUMENT_EXCHANGE_RATE_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate({**material, "scan_id": "erfdsv1:scan:" + canonical_json_sha256_v1(material)})


def validate_exchange_rate_full_document_scan_replay_v1(
    value: Any, semantic_index: Any
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_exchange_rate_full_document_scan_v1(semantic_index)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("exchange-rate scan does not replay exactly")
    return supplied


def _stable_json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != EXPECTED_INDEX_SHA256:
        raise _error("fixed full-document semantic index drifted")
    import json

    value = json.loads(payload)
    if type(value) is not dict:
        raise _error("semantic index root drifted")
    return value


def build_live_exchange_rate_full_document_scan_v1(
    input_path: Path = DEFAULT_INPUT,
) -> dict[str, Any]:
    return build_exchange_rate_full_document_scan_v1(_stable_json(PROJECT_ROOT / input_path))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    value = build_live_exchange_rate_full_document_scan_v1(args.input)
    import json

    print(json.dumps(value, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
