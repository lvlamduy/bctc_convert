#!/usr/bin/env python3
"""Scan annual-2025 capital-and-funds tables with reporting-period-general rules.

The predecessor graph was calibrated on interim filings and treated 30 June or
31 March as the closing boundary.  This version keeps the same bank-blind
owner/column/movement topology, but admits any two distinct authenticated
balance-date boundaries and the annual wording ``tình hình tăng giảm``.  A
split ``Triệu``/``VND`` unit header is recomposed in the same way as a merged
``Triệu VND`` header.  Continuation owners cannot start a second region.

Bank, filename, page, note number and reporting year are evidence locators only;
none participates in matching.  Rotated pages are selected by the pre-existing
geometry-only rule and re-read by the same VietOCR Transformer.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
EXPECTED_INPUT_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_SEMANTIC_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_RESCUE_PROJECTION_ID = (
    "fdrrv1:projection:6ef48add635631c2ee6d96b309002fcbc79c2b9576351b7f5afc4463ab3a2fc7"
)
EXPECTED_RESCUE_REFS = {
    "crop_manifest": (
        "680c5981dcf0fba79b969fb33d14f15b418956d390cd541443475a4435289e45",
        2_139_367,
    ),
    "ocr_result": (
        "a7c04bdb9dafb0b2017525ef83dbf8c672230cc4bbb04ba957c4c52cb7d904a4",
        1_798_255,
    ),
    "reader_request": (
        "1b537bbad4b49d7e31389e4a42f37169305be0e907143d824c1c8d4223eedd43",
        955_265,
    ),
    "run_manifest": (
        "7b1507167dc21ff337500b7248b692f5d133fe59da63f996338c5830e9f22042",
        3_161,
    ),
}
EXPECTED_RESCUE_METRICS = {"document_count": 3, "line_count": 3_338, "page_count": 25}

FORMAT_VERSION = "ANNUAL_2025_CAPITAL_AND_FUNDS_FULL_DOCUMENT_SCAN_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_CAPITAL_FUNDS_OWNER_OPTIONAL_CHANGE_HEADING_EQUITY_COLUMNS_"
    "DISTINCT_BALANCE_DATES_MOVEMENTS_UNIT_TOTAL_AND_GEOMETRY_SELECTED_ROTATED_"
    "SAME_TRANSFORMER_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_page_or_year_used_as_matching_or_routing": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "reporting_period_inferred_from_distinct_visible_balance_dates": True,
    "rotated_rescue_selected_by_geometry_not_bank_or_page": True,
    "text_similarity_alone_can_accept": False,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "scan_id",
    "state",
    "trials",
}
_EQUITY_CORE = {
    "CAPITAL_RESERVE",
    "DEVELOPMENT_FUND",
    "FINANCIAL_RESERVE",
    "FX_DIFFERENCE",
    "NONCONTROLLING_INTEREST",
    "OTHER_CAPITAL",
    "OTHER_RESERVES",
    "RETAINED_EARNINGS",
    "SHARE_PREMIUM",
}
_BALANCE_ROLES = {
    "BALANCE_AXIS",
    "CLOSING_BALANCE",
    "CLOSING_PERIOD_AXIS",
    "INTERMEDIATE_OR_OPENING_BALANCE",
    "OPENING_BALANCE",
    "OPENING_PERIOD_AXIS",
}
_DATE_BOUNDARY = re.compile(r"\b([0-3]?\d)\s+(?:thang\s+)?([01]?\d)\s+(?:nam\s+)?(20[0-9a-z]{2})\b")
_OCR_YEAR_DIGITS = str.maketrans({"i": "1", "l": "1", "o": "0", "s": "5"})


class Annual2025CapitalAndFundsFullDocumentScanV1Error(ValueError):
    """The pinned source, rotated rescue, or annual graph drifted."""


def _error(message: str) -> Annual2025CapitalAndFundsFullDocumentScanV1Error:
    return Annual2025CapitalAndFundsFullDocumentScanV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual capital support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stable_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    absolute = PROJECT_ROOT / path
    before = absolute.stat()
    payload = absolute.read_bytes()
    after = absolute.stat()
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        raise _error(f"annual capital input changed while read: {path}")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"annual capital input is not strict JSON: {path}") from exc
    if type(value) is not dict:
        raise _error(f"annual capital input must be one object: {path}")
    return value


def _configured_modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    matcher = _load_module(
        "annual_2025_capital_and_funds_matcher_v1",
        "capital_and_funds_variant_graph_v1.py",
    )
    scanner = _load_module(
        "annual_2025_capital_and_funds_base_scanner_v1",
        "scan_capital_and_funds_full_document_vietocr_v1.py",
    )
    rescue_builder = _load_module(
        "annual_2025_capital_and_funds_rotated_rescue_v1",
        "build_full_document_rotated_vietocr_rescue_v1.py",
    )
    matcher._CHANGE_HEADING_ALIASES = (
        *matcher._CHANGE_HEADING_ALIASES,
        "Tình hình tăng giảm vốn chủ sở hữu",
    )
    original_axis_role = matcher._axis_role

    def _annual_axis_role(text: str) -> str | None:
        if matcher._strip_enumerator(text) in {"trieu", "vnd"}:
            return "UNIT_AXIS"
        return original_axis_role(text)

    matcher._axis_role = _annual_axis_role
    scanner._matcher = lambda: matcher
    scanner._EXPECTED_RESCUE_REFS = EXPECTED_RESCUE_REFS
    scanner._EXPECTED_RESCUE_METRICS = EXPECTED_RESCUE_METRICS
    scanner._EXPECTED_SEMANTIC_AXIS_SHA256 = EXPECTED_SEMANTIC_AXIS_SHA256
    rescue_builder._activate_profile("annual-2025")
    return matcher, scanner, rescue_builder


def _balance_boundary_key(text: str) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(text)
    if "so du dau nam" in normalized:
        return "OPENING_YEAR"
    if "so du cuoi nam" in normalized:
        return "CLOSING_YEAR"
    match = _DATE_BOUNDARY.search(normalized)
    if match is None:
        return None
    day, month, raw_year = match.groups()
    year = raw_year.translate(_OCR_YEAR_DIGITS)
    if not year.isdigit():
        return None
    numeric_day = int(day)
    numeric_month = int(month)
    numeric_year = int(year)
    if not (1 <= numeric_day <= 31 and 1 <= numeric_month <= 12 and 2000 <= numeric_year <= 2099):
        return None
    return f"{numeric_year:04d}-{numeric_month:02d}-{numeric_day:02d}"


def _balance_keys(region: dict[str, Any]) -> list[str]:
    keys = {
        key
        for event in region["events"]
        if event["role"] in _BALANCE_ROLES
        if (key := _balance_boundary_key(event["vietocr_text"])) is not None
    }
    return sorted(keys)


def _is_complete_annual_region(region: dict[str, Any]) -> bool:
    layout = region["layout"]
    child_roles = set(layout["child_roles"])
    movement_roles = set(layout["movement_roles"])
    owner = normalize_vietnamese_anchor_v1(region["owner"]["vietocr_text"])
    boundary_complete = {"OPENING_BALANCE", "CLOSING_BALANCE"}.issubset(movement_roles) or len(
        _balance_keys(region)
    ) >= 2
    return (
        "tiep theo" not in owner
        and layout["change_heading_count"] >= 1
        and "CAPITAL" in child_roles
        and len(child_roles & _EQUITY_CORE) >= 2
        and boundary_complete
        and region["numeric_line_count"] >= 10
        and layout["unit_axis_line_count"] >= 1
    )


def _selected_region(base_result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    candidates = [*base_result["regions"], *base_result["near_regions"]]
    selected = [candidate for candidate in candidates if _is_complete_annual_region(candidate)]
    if len(selected) != 1:
        raise _error(
            "annual capital graph must produce exactly one complete region after all controls"
        )
    region = canonical_clone_v1(selected[0])
    region["annual_complete"] = True
    region["annual_completion_evidence"] = {
        "balance_boundary_keys": _balance_keys(region),
        "continuation_owner_used_as_region_start": False,
        "distinct_balance_boundary_count": len(_balance_keys(region)),
        "split_unit_header_supported": True,
    }
    return region, len(candidates) - 1


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(trials),
        "document_count": len(trials),
        "document_multiple_complete_region_count": sum(
            trial["annual_complete_region_count"] != 1 for trial in trials
        ),
        "document_unique_structural_match_count": sum(
            trial["annual_complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": 0,
        "negative_control_region_count": sum(
            trial["negative_control_region_count"] for trial in trials
        ),
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
        "unresolved_document_count": sum(
            trial["annual_complete_region_count"] != 1 for trial in trials
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual capital scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_CAPITAL_AND_FUNDS_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual capital scan identity or metrics drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial)
            != {
                "annual_complete_region_count",
                "base_matcher_result",
                "document_ordinal",
                "document_provenance",
                "negative_control_region_count",
                "rotated_rescue_line_count",
                "selected_region",
                "source_pdf_sha256",
            }
            or trial["document_ordinal"] != ordinal
            or trial["annual_complete_region_count"] != 1
            or type(trial["selected_region"]) is not dict
        ):
            raise _error("annual capital scan trial drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "a2025caffdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("annual capital scan identity drifted")
    return canonical_clone_v1(value)


def build_annual_2025_capital_and_funds_full_document_scan_v1() -> dict[str, Any]:
    semantic_index = _stable_json(INPUT_PATH, EXPECTED_INPUT_SHA256)
    matcher, scanner, rescue_builder = _configured_modules()
    rescue = scanner._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    if rescue["projection_id"] != EXPECTED_RESCUE_PROJECTION_ID:
        raise _error("annual capital rotated-rescue projection drifted")
    axis = scanner.project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_SEMANTIC_AXIS_SHA256:
        raise _error("annual capital semantic axis drifted")
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    trials = []
    total_applied = 0
    for document in axis["documents"]:
        pages, applied = scanner._matcher_pages(document, rescue_by_locator)
        total_applied += applied
        base_result = matcher.build_capital_and_funds_variant_graph_document_v1(pages)
        selected, negative_count = _selected_region(base_result)
        trials.append(
            {
                "annual_complete_region_count": 1,
                "base_matcher_result": base_result,
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "negative_control_region_count": negative_count,
                "rotated_rescue_line_count": applied,
                "selected_region": selected,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if total_applied != EXPECTED_RESCUE_METRICS["line_count"]:
        raise _error("annual capital rotated rescue was not consumed exactly once")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "rotated_rescue_projection_id": rescue["projection_id"],
            "semantic_axis_projection_id": axis["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INPUT_SHA256,
        },
        "metrics": _metrics(trials),
        "state": "ANNUAL_2025_CAPITAL_AND_FUNDS_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate(
        {**material, "scan_id": "a2025caffdsv1:scan:" + canonical_json_sha256_v1(material)}
    )


def validate_annual_2025_capital_and_funds_full_document_scan_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_annual_2025_capital_and_funds_full_document_scan_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual capital scan does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = build_annual_2025_capital_and_funds_full_document_scan_v1()
    payload = canonical_json_bytes_v1(value)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
