#!/usr/bin/env python3
"""Scan annual-2025 liquidity-risk tables with the existing graph engine.

The historical family graph remains bank/page blind.  This annual adapter
changes only header reconstruction: it composes vertically split cells from
their geometry, retains multiple semantic axes when one OCR line spans
adjacent physical columns, and tolerates bounded one-character digit errors
inside an otherwise complete maturity range.  Numeric columns are not read or
mapped here.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import statistics
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
FORMAT_VERSION = "ANNUAL_2025_LIQUIDITY_RISK_8DOCUMENT_FULL_VIETOCR_SCAN_V1"
MATCHER_FORMAT = "LIQUIDITY_RISK_VARIANT_GRAPH_DOCUMENT_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_LIQUIDITY_RISK_MULTILINE_OR_MERGED_MATURITY_HEADER_ASSET_"
    "LIABILITY_GAP_AND_GEOMETRY_SELECTED_ROTATED_SAME_TRANSFORMER_STRUCTURE_"
    "ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_page_or_year_used_as_matching_or_routing": False,
    "bounded_detailed_table_absence_only": True,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "merged_header_may_represent_multiple_physical_axes": True,
    "numeric_authority": False,
    "pair_first_variant_graph_used": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_rescue_selected_by_geometry_not_bank_or_page": True,
    "text_similarity_alone_can_accept": False,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_axis_projection_id",
    "input_rescue",
    "input_semantic_axis_sha256",
    "metrics",
    "scan_id",
    "state",
    "trials",
}


class Annual2025LiquidityRiskFullDocumentScanV1Error(ValueError):
    """The annual source, rescue input or liquidity graph drifted."""


def _error(message: str) -> Annual2025LiquidityRiskFullDocumentScanV1Error:
    return Annual2025LiquidityRiskFullDocumentScanV1Error(message)


def _load(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual liquidity-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _annual_support() -> ModuleType:
    return _load(
        "annual_2025_liquidity_risk_fixed_input_support_v1",
        "scan_annual_2025_interest_rate_risk_full_document_vietocr_v1.py",
    )


def _annual_axis_roles(matcher: ModuleType, original_axis_role: Any, text: str) -> list[str]:
    value = matcher._strip(text)
    roles: list[str] = []
    # Range anchors are interpreted from the complete vertically composed
    # header surface.  A single OCR-confused endpoint is allowed only when the
    # start, unit and ordered range topology are all visible.
    if re.search(
        r"\btu\s*(?:tren\s+)?0?1\s+(?:thang\s+)?(?:den|[-?])\s*"
        r"(?:0?[3o]|[a-z])\s*thang\b",
        value,
    ) or ("tu tren 1 thang" in value and "den" in value):
        roles.append("WITHIN_1_3M")
    if re.search(
        r"\btu\s*(?:tren\s+)?(?:0?[3-5]|[a-z])(?:\s+thang)?\s*"
        r"(?:den|-)?\s*12\s+(?:thang|mang)\b",
        value,
    ):
        roles.append("WITHIN_3_12M")
    if re.search(
        r"\btu\s*(?:tren\s+)?0?1\s+nam.*\bden\s+(?:0?5|[a-z])\s+nam\b",
        value,
    ):
        roles.append("WITHIN_1_5Y")

    original = original_axis_role(text)
    if original is not None:
        roles.append(original)
    if re.search(r"\bden\s+0?1\s+thang\b", value):
        roles.append("WITHIN_LE1M")
    if re.search(r"\btren\s+0?3\s+thang\b", value):
        roles.append("OVERDUE_GT3M")
    if re.search(r"\bden\s+0?3\s+thang\b", value) and "tu tren 1" not in value:
        roles.append("OVERDUE_LE3M")
    if value in {"tong", "tong cong", "tang"}:
        roles.append("TOTAL")
    return list(dict.fromkeys(roles))


def _configured_modules() -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    matcher = _load(
        "annual_2025_liquidity_risk_matcher_v1",
        "liquidity_risk_variant_graph_v1.py",
    )
    annual = _annual_support()
    _interest_matcher, rotated_support, rescue_builder = annual._configured_modules()
    original_axis_role = matcher._axis_role

    def annual_header_features(
        page: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]], int]:
        support = matcher._support()
        if not page["lines"]:
            return [], [], 0
        body_roles = matcher._ASSET_ROLES | {
            "ASSET_SECTION",
            "ASSET_TOTAL",
            "DERIVATIVE_ROW",
            "INTERBANK_ROW",
        }
        body_lines = [
            line
            for line in page["lines"]
            if matcher._raw_role(line["normalized_text"]) in body_roles
        ]
        cutoff_y = min(
            (line["bbox"][1] for line in body_lines),
            default=max(line["bbox"][3] for line in page["lines"]),
        )
        header = [line for line in page["lines"] if line["bbox"][1] < cutoff_y]
        if not header:
            return [], [], 0
        median_height = statistics.median(line["bbox"][3] - line["bbox"][1] for line in header)
        vertical_tolerance = max(median_height * 3.8, 120)
        candidates: list[tuple[str, dict[str, Any], str]] = []
        for line in header:
            aligned = sorted(
                (
                    other
                    for other in header
                    if min(line["bbox"][2], other["bbox"][2])
                    - max(line["bbox"][0], other["bbox"][0])
                    >= -min(
                        line["bbox"][2] - line["bbox"][0],
                        other["bbox"][2] - other["bbox"][0],
                    )
                    * 0.05
                    and abs(
                        (other["bbox"][1] + other["bbox"][3]) - (line["bbox"][1] + line["bbox"][3])
                    )
                    / 2
                    <= vertical_tolerance
                ),
                key=lambda item: (item["bbox"][1], item["bbox"][0]),
            )
            composed = " ".join(item["normalized_text"] for item in aligned)
            roles = _annual_axis_roles(matcher, original_axis_role, composed)
            if not roles:
                roles = _annual_axis_roles(matcher, original_axis_role, line["normalized_text"])
            candidates.extend((role, line, composed) for role in roles)

        best: dict[str, tuple[dict[str, Any], str, tuple[int, int]]] = {}
        for role, line, composed in candidates:
            rank = (line["bbox"][2] - line["bbox"][0], -line["bbox"][1])
            if role not in best or rank < best[role][2]:
                best[role] = (line, composed, rank)
        if {"OVERDUE_GT3M", "OVERDUE_LE3M"} & set(best):
            best.pop("OVERDUE", None)
        semantic_order = {
            "OVERDUE_GT3M": 0,
            "OVERDUE_LE3M": 1,
            "WITHIN_LE1M": 2,
            "WITHIN_1_3M": 3,
            "WITHIN_3_12M": 4,
            "WITHIN_1_5Y": 5,
            "WITHIN_GT5Y": 6,
            "TOTAL": 7,
        }
        axes = sorted(
            best,
            key=lambda role: (
                semantic_order.get(role, 99),
                (best[role][0]["bbox"][0] + best[role][0]["bbox"][2]) / 2,
            ),
        )
        unit_lines = [line for line in header if matcher._unit(line["normalized_text"])]
        events = [support._line_ref(best[role][0], f"MATURITY_AXIS_{role}") for role in axes]
        events.extend(support._line_ref(line, "UNIT_AXIS") for line in unit_lines)
        return axes, events, len(unit_lines)

    matcher._header_features = annual_header_features
    return matcher, rotated_support, rescue_builder, annual


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    unique = sum(
        trial["matcher_result"]["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
    )
    return {
        "bounded_detailed_table_absence_count": len(trials) - unique,
        "complete_region_count": sum(
            trial["matcher_result"]["metrics"]["complete_region_count"] for trial in trials
        ),
        "complete_table_page_count": sum(
            trial["matcher_result"]["metrics"]["complete_table_page_count"] for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structural_match_count": unique,
        "mapping_verified_count": 0,
        "near_region_count": sum(
            trial["matcher_result"]["metrics"]["near_region_count"] for trial in trials
        ),
        "rotated_rescue_line_count": sum(trial["rotated_rescue_line_count"] for trial in trials),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual liquidity-risk scan fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_LIQUIDITY_RISK_SCAN_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual liquidity-risk scan identity or metrics drifted")
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
                "rotated_rescue_line_count",
                "source_pdf_sha256",
            }
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or type(trial["matcher_result"]) is not dict
            or trial["matcher_result"].get("format_version") != MATCHER_FORMAT
            or type(trial["rotated_rescue_line_count"]) is not int
        ):
            raise _error("annual liquidity-risk trial identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != "a2025lrrfdsv1:scan:" + canonical_json_sha256_v1(material):
        raise _error("annual liquidity-risk scan ID drifted")
    return canonical_clone_v1(value)


def build_annual_2025_liquidity_risk_full_document_scan_v1() -> dict[str, Any]:
    matcher, rotated_support, rescue_builder, annual = _configured_modules()
    semantic_index = annual._stable_json(annual.INPUT_PATH, annual.EXPECTED_INPUT_SHA256)
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    if rescue["projection_id"] != annual.EXPECTED_RESCUE_PROJECTION_ID:
        raise _error("annual liquidity-risk rotated-rescue projection drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != annual.EXPECTED_SEMANTIC_AXIS_SHA256:
        raise _error("annual liquidity-risk semantic axis drifted")
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    trials = []
    total_applied = 0
    for document in axis["documents"]:
        pages, applied = rotated_support._matcher_pages(document, rescue_by_locator)
        total_applied += applied
        trials.append(
            {
                "document_ordinal": document["document_ordinal"],
                "document_provenance": document["document_provenance"],
                "matcher_result": matcher.build_liquidity_risk_variant_graph_document_v1(pages),
                "rotated_rescue_line_count": applied,
                "source_pdf_sha256": document["source_pdf"]["sha256"],
            }
        )
    if total_applied != annual.EXPECTED_RESCUE_METRICS["line_count"]:
        raise _error("annual liquidity-risk rotated rescue was not consumed exactly once")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_axis_projection_id": axis["projection_id"],
        "input_rescue": {
            "input_refs": rescue["input_refs"],
            "metrics": rescue["metrics"],
            "projection_id": rescue["projection_id"],
        },
        "input_semantic_axis_sha256": axis["semantic_axis_sha256"],
        "metrics": _metrics(trials),
        "state": "ANNUAL_2025_LIQUIDITY_RISK_SCAN_COMPLETE",
        "trials": trials,
    }
    return _validate(
        {
            **material,
            "scan_id": "a2025lrrfdsv1:scan:" + canonical_json_sha256_v1(material),
        }
    )


def validate_annual_2025_liquidity_risk_full_document_scan_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_annual_2025_liquidity_risk_full_document_scan_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual liquidity-risk scan does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    sys.stdout.buffer.write(
        canonical_json_bytes_v1(build_annual_2025_liquidity_risk_full_document_scan_v1())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
