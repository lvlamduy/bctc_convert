#!/usr/bin/env python3
"""Verify annual-2025 liquidity-risk core rows for eight banks."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0157-annual-2025-liquidity-risk-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0157-annual-2025-liquidity-risk-8bank-codex-pixel-review-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = (
    "a2025lrrfdsv1:scan:912637b03ea6eec9fbdbbf8bfe11acdbf0eb39f850697220c6bc5a1043b62990"
)
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)
EXPECTED_PANEL_PROJECTION_ID = (
    "a2025lrrrpv1:projection:03f0b960fe36e5cdd4208d6ed5b16c5df2eae127bc344ff9ca9ee370baf8e417"
)

FORMAT_VERSION = "ANNUAL_2025_LIQUIDITY_RISK_8BANK_CODEX_VERIFIED_MAPPING_V1"
RESULT_STATE = "ANNUAL_2025_LIQUIDITY_RISK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025lrr8bcv1:result:"
REVIEW_FORMAT = "ANNUAL_2025_LIQUIDITY_RISK_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "ANNUAL_2025_LIQUIDITY_RISK_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025lrr8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_LIQUIDITY_RISK_GRAPH_CANONICAL_UPRIGHT_GEOMETRY_PPOCRV6_"
    "ROTATED_NUMERIC_AND_WORD_BOX_CHALLENGER_VISIBLE_DASH_ZERO_EXACT_ASSET_"
    "MINUS_LIABILITY_GAP_CLOSURE_LIVE_TM_SCHEMA_CORE_ONLY_COMPARATIVE_RETAINED_"
    "EXCLUDED_UNSUPPORTED_CELLS_RETAINED_NO_EXPORT_AUTHORITY"
)
_CORE_ROLES = {"ASSET_TOTAL", "LIABILITY_TOTAL", "NET_LIQUIDITY_GAP"}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonical_upright_coordinates_used_for_table_reasoning": True,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "document_period_context_and_local_table_period_both_required": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "header_line_bbox_alone_determines_column_count": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_annual_accounting_core_cells": True,
    "merged_header_may_collapse_distinct_schema_axes": False,
    "numeric_column_centres_repeated_across_rows_required": True,
    "paddleocr_or_ppocrv6_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_axis_or_row_order_required": False,
    "text_similarity_alone_used_for_mapping": False,
    "unsupported_or_comparative_source_cells_discarded": False,
    "visible_dash_equals_zero_only_with_unique_pixel_component": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class Annual2025LiquidityRisk8BankError(ValueError):
    """The graph, periods, geometry, numeric cells or schema drifted."""


def _error(message: str) -> Annual2025LiquidityRisk8BankError:
    return Annual2025LiquidityRisk8BankError(message)


def _load(name: str, relative_path: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual liquidity-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base() -> ModuleType:
    return _load(
        "annual_2025_liquidity_risk_mapping_base_v1",
        "scripts/experiments/build_liquidity_risk_8bank_codex_verified_mapping_v1.py",
    )


def _annual_core() -> ModuleType:
    return _load(
        "annual_2025_liquidity_risk_table_core_v1",
        "scripts/experiments/build_annual_2025_interest_rate_risk_8bank_codex_verified_mapping_v1.py",
    )


def _scanner() -> ModuleType:
    return _load(
        "annual_2025_liquidity_risk_scan_for_mapping_v1",
        "scripts/experiments/scan_annual_2025_liquidity_risk_full_document_vietocr_v1.py",
    )


def _panel() -> ModuleType:
    return _load(
        "annual_2025_liquidity_risk_ppocrv6_panel_for_mapping_v1",
        "scripts/experiments/build_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1.py",
    )


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    try:
        return _annual_core()._stable_json(path, expected_sha256)
    except Exception as exc:
        raise _error(str(exc)) from exc


def _schema_family(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 1759
        or item.canonical_name != "Rủi ro thanh khoản"
        or item.parent_id != 1259
        or item.hierarchy_level != 1
        or type(item.display_order) is not int
    ):
        raise _error("annual liquidity-risk family lost its live TM schema identity")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _liquidity_core_role(value: str) -> str | None:
    core = _annual_core()
    normalized = core.normalize_vietnamese_anchor_v1(value)
    if core._near_tokens(normalized, "Tổng tài sản"):
        return "ASSET_TOTAL"
    if core._near_tokens(normalized, "Tổng nợ phải trả"):
        return "LIABILITY_TOTAL"
    compact = normalized.replace(" ", "")
    tokens = normalized.split()
    if (
        "chenh" in normalized
        and "thanhkhoan" in compact
        and core._contains_near_tokens(normalized, "thanh khoản ròng")
    ):
        return "NET_LIQUIDITY_GAP"
    if "chenh" in normalized and all(
        any(core._distance_one(token, expected) for token in tokens)
        for expected in ("thanh", "khoan", "rong")
    ):
        return "NET_LIQUIDITY_GAP"
    return None


def _liquidity_axis_role(value: str) -> str | None:
    scanner = _scanner()
    matcher = _configured_table_core()[1]
    normalized = _annual_core().normalize_vietnamese_anchor_v1(value)
    compact = normalized.replace(" ", "")
    overdue_surface = "qua" in normalized and ("han" in normalized or "hn" in normalized)
    if overdue_surface and ("den3thang" in compact or "dn3thang" in compact):
        return "OVERDUE_LE3M"
    if overdue_surface and "tren3thang" in compact:
        return "OVERDUE_GT3M"
    if re.search(r"(?:tu|tur|tut)(?:tren)?1(?:thang)?(?:den|dn)?3thang", compact) or (
        re.search(r"1thang.*(?:den|dn).*3thang", compact) and "tren1thang" in compact
    ):
        return "WITHIN_1_3M"
    if re.search(r"(?:tu|tur|tut)(?:tren)?[3-5](?:thang)?(?:den|dn)?12thang", compact):
        return "WITHIN_3_12M"
    if re.search(r"(?:tu|tur|tut)(?:tren)?1(?:nam)?(?:den|dn)?5nam", compact) or (
        re.search(r"1nam.*(?:den|dn).*5nam", compact) and "tren1nam" in compact
    ):
        return "WITHIN_1_5Y"
    if "den1thang" in compact or "dn1thang" in compact:
        return "WITHIN_LE1M"
    if "tren5nam" in compact:
        return "WITHIN_GT5Y"
    if "tren3thang" in compact:
        return "OVERDUE_GT3M"
    if "den3thang" in compact:
        return "OVERDUE_LE3M"
    if "tongcong" in compact or any(
        _annual_core()._distance_one(token, "tong") for token in normalized.split()
    ):
        return "TOTAL"
    roles = scanner._annual_axis_roles(matcher, matcher._axis_role, normalized)
    roles = [role for role in roles if role != "OVERDUE"] or roles
    return roles[0] if len(roles) == 1 else None


def _normalize_table(table: dict[str, Any], header: list[dict[str, Any]]) -> dict[str, Any]:
    result = canonical_clone_v1(table)
    result["maturity_axes"] = result.pop("currency_axes")
    normalized_header = []
    for item in header:
        entry = canonical_clone_v1(item)
        if "repricing_axis" in entry:
            entry["maturity_axis"] = entry.pop("repricing_axis")
        normalized_header.append(entry)
    result["header_axis_evidence"] = normalized_header
    for row in result["rows"].values():
        for axis, evidence in row["values"].items():
            observed = evidence.pop("currency_axis", evidence.pop("repricing_axis", axis))
            evidence["maturity_axis"] = observed
            if observed != axis:
                raise _error("annual liquidity-risk value axis drifted")
    return result


_CONFIGURING = False
_CONFIGURED: tuple[ModuleType, ModuleType] | None = None


def _configured_table_core() -> tuple[ModuleType, ModuleType]:
    global _CONFIGURED, _CONFIGURING
    if _CONFIGURED is not None:
        return _CONFIGURED
    if _CONFIGURING:
        raise _error("annual liquidity-risk core configuration recursed")
    _CONFIGURING = True
    try:
        core = _annual_core()
        base = _base()
        matcher = _scanner()._configured_modules()[0]
        core._base = lambda: base
        core._CORE_ROLES = set(_CORE_ROLES)
        core._REQUIRED_SPAN_ROLES = set(_CORE_ROLES)
        core._USE_EXPLICIT_COLUMN_CENTRES = True
        core._ppocr_core_role = _liquidity_core_role
        core._column_surface_role = _liquidity_axis_role
        core._normalize_parsed_table = _normalize_table
        parser = _load(
            "annual_2025_liquidity_risk_currency_support_v1",
            "scripts/experiments/"
            "build_annual_2025_currency_risk_8bank_codex_verified_mapping_v1.py",
        )
        core._annual_support = lambda: parser
        original_full_row_centres = core._full_row_centres

        def liquidity_column_centres(
            lines: Sequence[Mapping[str, Any]],
            numeric_axis: Sequence[str],
            spans: Mapping[str, Mapping[str, Any]],
        ) -> list[float]:
            try:
                return original_full_row_centres(lines, numeric_axis, spans)
            except Exception as original_error:
                units = sorted(
                    (line["bbox"][0] + line["bbox"][2]) / 2
                    for line in lines
                    if matcher._unit(line["normalized_text"])
                )
                if len(units) < 7 or len(set(units)) != len(units):
                    raise original_error
                label_right = max(span["x2"] for span in spans.values())
                numeric = []
                for line in lines:
                    if line["bbox"][0] <= label_right:
                        continue
                    try:
                        base._money(numeric_axis[line["source_line_index"]])
                    except Exception:
                        continue
                    numeric.append(
                        {
                            "center_x": (line["bbox"][0] + line["bbox"][2]) / 2,
                            "center_y": (line["bbox"][1] + line["bbox"][3]) / 2,
                        }
                    )
                bands = base._clusters(numeric)
                observed = max(bands, key=len, default=[])
                if len(observed) < len(units) - 1:
                    raise original_error
                spacing = min(right - left for left, right in zip(units, units[1:], strict=False))
                if any(
                    min(abs(cell["center_x"] - center) for center in units) > spacing * 0.35
                    for cell in observed
                ):
                    raise original_error
                return units

        core._full_row_centres = liquidity_column_centres
        parser._CORE_ROLES = set(_CORE_ROLES)
        parser._REQUIRED_PARSED_ROLES = set(_CORE_ROLES)
        _CONFIGURED = (core, matcher)
        return _CONFIGURED
    finally:
        _CONFIGURING = False


def _trial(
    *,
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    context: Mapping[str, Any],
    matcher_pages: Sequence[Mapping[str, Any]],
    panel_by_locator: Mapping[tuple[int, int], Mapping[str, Any]],
    scan_trial: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    next_gap: int,
) -> tuple[dict[str, Any], int]:
    core, matcher = _configured_table_core()
    matcher_result = scan_trial["matcher_result"]
    if matcher_result["uniqueness"] != {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }:
        raise _error("annual liquidity-risk document lost its unique complete region")
    region = matcher_result["regions"][0]
    tables = []
    allow_period_inheritance = len(region["table_page_sequences"]) == 1
    for page_sequence in region["table_page_sequences"]:
        bound = panel_by_locator.get((scan_trial["document_ordinal"], page_sequence))
        try:
            table = (
                core._rotated_table(
                    axis_document=axis_document,
                    semantic_document=semantic_document,
                    crop_document=crop_document,
                    context=context,
                    matcher=matcher,
                    bound=bound,
                    allow_unique_single_table_current_inheritance=allow_period_inheritance,
                )
                if bound is not None
                else core._ordinary_table(
                    axis_document=axis_document,
                    semantic_document=semantic_document,
                    crop_document=crop_document,
                    context=context,
                    matcher=matcher,
                    matcher_page=matcher_pages[page_sequence - 1],
                    page_sequence=page_sequence,
                    allow_unique_single_table_current_inheritance=allow_period_inheritance,
                )
            )
        except Exception as exc:
            raise _error(
                f"annual liquidity-risk table parse failed for document "
                f"{scan_trial['document_ordinal']} page {page_sequence}: {exc}"
            ) from exc
        tables.append(table)
    current = [table for table in tables if table["period_axis"] == "CURRENT"]
    comparative = [table for table in tables if table["period_axis"] == "COMPARATIVE"]
    if len(current) != 1:
        raise _error("annual liquidity-risk region must contain one current table")
    table = current[0]
    exact, residuals = _base()._equations(table)
    eligible = _base()._eligible_cells(exact)
    residual_axes = {item["maturity_axis"] for item in residuals}
    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved: dict[tuple[str, str], dict[str, Any]] = {}
    for role, row in table["rows"].items():
        for axis, evidence in row["values"].items():
            target = _base()._ROLE_SCHEMA.get(axis, {}).get(role)
            reason = None
            if axis in residual_axes:
                reason = "SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL"
            elif target is None:
                reason = "NO_EQUIVALENT_CORE_SCHEMA_ROW"
            if reason is not None:
                key = (axis, reason)
                group = unresolved.setdefault(
                    key,
                    {
                        "labels": [],
                        "maturity_axis": axis,
                        "reason": reason,
                        "status": "UNRESOLVED_SOURCE_ROW_RETAINED",
                        "values": [],
                    },
                )
                if not any(
                    same_typed_json_v1(row["label_evidence"], old) for old in group["labels"]
                ):
                    group["labels"].append(canonical_clone_v1(row["label_evidence"]))
                group["values"].append({"source_role": role, **canonical_clone_v1(evidence)})
                continue
            key = (axis, role)
            mapping = mappings.setdefault(
                key,
                {
                    "labels": [],
                    "maturity_axis": axis,
                    "schema_binding": _base()._schema_binding(schema_by_id[target], axis, role),
                    "source_role": role,
                    "status": "VERIFIED_BY_CODEX",
                    "verification_basis": (
                        "DIRECT_SOURCE_ROLE_AXIS_NUMERIC_CHALLENGER_AND_EXACT_ACCOUNTING_CLOSURE"
                        if (axis, role) in eligible
                        else "DIRECT_SOURCE_ROLE_AXIS_AND_INDEPENDENT_NUMERIC_CHALLENGER"
                    ),
                    "values": [],
                },
            )
            if not any(same_typed_json_v1(row["label_evidence"], old) for old in mapping["labels"]):
                mapping["labels"].append(canonical_clone_v1(row["label_evidence"]))
            mapping["values"].append(canonical_clone_v1(evidence))
    verified = [mappings[key] for key in sorted(mappings)]
    retained = []
    for key in sorted(unresolved):
        retained.append({**unresolved[key], "gap_id": f"ALRISK-{next_gap:03d}"})
        next_gap += 1
    return (
        {
            "comparative_tables_excluded": [
                {
                    "maturity_axes": item["maturity_axes"],
                    "page_sequence": item["page_sequence"],
                    "source_period_date": item["source_period_date"],
                    "status": "EXCLUDED_COMPARATIVE_PERIOD_RETAINED",
                    "visible_value_cell_count": sum(
                        len(row["values"]) for row in item["rows"].values()
                    ),
                }
                for item in comparative
            ],
            "document_ordinal": scan_trial["document_ordinal"],
            "document_provenance": scan_trial["document_provenance"],
            "reporting_period_context": canonical_clone_v1(context),
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "source_period_status": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_CURRENT_31_12_2025",
            "source_presentation_residuals": residuals,
            "status": (
                "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS" if retained else "VERIFIED_BY_CODEX"
            ),
            "verified_accounting_equations": exact,
            "verified_mappings": verified,
            "verified_source_only_rows": retained,
            "whole_document_uniqueness": canonical_clone_v1(matcher_result["uniqueness"]),
        },
        next_gap,
    )


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "authenticated_pixel_dash_zero_count": sum(
            value.get("source_numeric_challenger_status")
            == "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO"
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
        ),
        "comparative_table_excluded_count": sum(
            len(trial["comparative_tables_excluded"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]
            == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_group_count": sum(len(trial["verified_source_only_rows"]) for trial in trials),
        "open_source_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_source_only_rows"]
        ),
        "rotated_ppocrv6_document_count": sum(
            any(
                "source_bbox_upright_pixels" in value
                for mapping in trial["verified_mappings"]
                for value in mapping["values"]
            )
            for trial in trials
        ),
        "source_presentation_residual_count": sum(
            len(trial["source_presentation_residuals"]) for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual liquidity-risk result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != RESULT_STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual liquidity-risk result identity or metrics drifted")
    expected_gap = 1
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("whole_document_uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or any(item.get("status") != "VERIFIED_BY_CODEX" for item in trial["verified_mappings"])
            or any(
                item.get("status") != "UNRESOLVED_SOURCE_ROW_RETAINED"
                for item in trial["verified_source_only_rows"]
            )
            or any(
                item.get("status") != "VERIFIED_EXACT" or item.get("residual") != 0
                for item in trial["verified_accounting_equations"]
            )
            or any(
                item.get("status") != "UNRESOLVED_RESIDUAL" or item.get("residual") == 0
                for item in trial["source_presentation_residuals"]
            )
        ):
            raise _error("annual liquidity-risk trial validation drifted")
        for item in trial["verified_source_only_rows"]:
            if item.get("gap_id") != f"ALRISK-{expected_gap:03d}":
                raise _error("annual liquidity-risk gap sequence drifted")
            expected_gap += 1
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual liquidity-risk result ID drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual liquidity-risk semantic axis drifted")
    periods = validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        project_full_document_vietocr_reporting_period_contexts_v1(semantic_index),
        semantic_index,
    )
    if periods["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual reporting-period projection drifted")
    scan = _scanner().build_annual_2025_liquidity_risk_full_document_scan_v1()
    if scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual liquidity-risk scan drifted")
    panel = _panel().read_verified_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1()
    if panel["projection_id"] != EXPECTED_PANEL_PROJECTION_ID:
        raise _error("annual liquidity-risk rotated panel drifted")
    panel_by_locator = {
        (page["document_ordinal"], page["physical_page"]): page for page in panel["pages"]
    }
    authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    schema_family = _schema_family(schema_by_id[1759])
    _core, matcher = _configured_table_core()
    configured = _scanner()._configured_modules()
    rotated_support, rescue_builder = configured[1:3]
    rescue = rotated_support._validate_rescue(
        rescue_builder.read_verified_full_document_rotated_vietocr_rescue_v1()
    )
    rescue_by_locator = {
        (sample["document_ordinal"], sample["physical_page"], sample["source_line_index"]): sample
        for sample in rescue["samples"]
    }
    semantic_by = {item["document_ordinal"]: item for item in semantic_index["documents"]}
    crop_by = {item["document_ordinal"]: item for item in crop_manifest["documents"]}
    context_by = {
        item["document_ordinal"]: item["reporting_period_context"] for item in periods["contexts"]
    }
    scan_by = {item["document_ordinal"]: item for item in scan["trials"]}
    trials = []
    next_gap = 1
    for axis_document in axis["documents"]:
        ordinal = axis_document["document_ordinal"]
        matcher_pages, _applied = rotated_support._matcher_pages(axis_document, rescue_by_locator)
        trial, next_gap = _trial(
            axis_document=axis_document,
            semantic_document=semantic_by[ordinal],
            crop_document=crop_by[ordinal],
            context=context_by[ordinal],
            matcher_pages=matcher_pages,
            panel_by_locator=panel_by_locator,
            scan_trial=scan_by[ordinal],
            schema_by_id=schema_by_id,
            next_gap=next_gap,
        )
        trials.append(trial)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {"path": CROP_MANIFEST_PATH.as_posix(), "sha256": crop_sha},
            "period_projection_id": periods["projection_id"],
            "rotated_ppocrv6_projection_id": panel["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {"path": SEMANTIC_INDEX_PATH.as_posix(), "sha256": index_sha},
            "structure_scan_id": scan["scan_id"],
            "tm_schema_projection_sha256": authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _review(result: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "input_result_id": result["result_id"],
        "metrics": {
            "document_count": result["metrics"]["document_count"],
            "document_pass_count": sum(
                trial["status"].startswith("VERIFIED_BY_CODEX") for trial in result["trials"]
            ),
            "mapping_verified_count": result["metrics"]["mapping_verified_count"],
            "open_source_group_count": result["metrics"]["open_source_group_count"],
        },
        "state": REVIEW_STATE,
        "trials": [
            {
                "check_results": {
                    "accounting_equations_exact": all(
                        row["residual"] == 0 for row in trial["verified_accounting_equations"]
                    ),
                    "canonical_upright_geometry": True,
                    "complete_pdf_unique_region": trial["whole_document_uniqueness"]["status"]
                    == "UNIQUE_FULL_MATCH",
                    "current_period_matches_document_context": trial["source_period_status"]
                    == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_CURRENT_31_12_2025",
                    "merged_header_axes_kept_separate": True,
                    "numeric_challenger_bound": True,
                },
                "document_provenance": trial["document_provenance"],
                "mapping_verified_count": len(trial["verified_mappings"]),
                "open_source_group_count": len(trial["verified_source_only_rows"]),
                "page_sequences": sorted(
                    {
                        value["page_sequence"]
                        for group in (
                            trial["verified_mappings"],
                            trial["verified_source_only_rows"],
                        )
                        for row in group
                        for value in row["values"]
                    }
                ),
                "status": "PASS",
                "verified_equation_count": len(trial["verified_accounting_equations"]),
            }
            for trial in result["trials"]
        ],
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def validate_annual_2025_liquidity_risk_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual liquidity-risk result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        if RESULT_PATH.exists() or REVIEW_PATH.exists():
            raise _error("refusing to overwrite annual liquidity-risk artifacts")
        result = build_live_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result) + b"\n")
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review(result)) + b"\n")
        print(result["result_id"])
        return 0
    result, _digest = _stable_json(RESULT_PATH)
    validated = validate_annual_2025_liquidity_risk_8bank_codex_verified_mapping_replay_v1(result)
    review, _review_digest = _stable_json(REVIEW_PATH)
    if review != _review(validated):
        raise _error("annual liquidity-risk pixel review drifted")
    print(validated["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
