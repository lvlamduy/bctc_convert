"""Verify the accounting core of currency-risk tables across eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load currency-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_currency_risk",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "currency_risk_scan_for_verified_mapping",
    "scan_currency_risk_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CURRENCY_RISK_8BANK_CODEX_VERIFIED_ACCOUNTING_CORE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_CURRENCY_"
    "RISK_GRAPH_AUTHENTICATED_SOURCE_NUMERIC_CHALLENGER_GEOMETRIC_COLUMN_"
    "ASSIGNMENT_EXACT_INTERNAL_AND_COMBINED_STATE_EQUATIONS_LIVE_TM_SCHEMA_"
    "CORE_ONLY_UNSUPPORTED_OR_NONCLOSING_AXES_RETAINED_NO_EXPORT_AUTHORITY"
)
RESULT_PATH = Path("docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json")
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "crfdsv1:scan:bbcbcd7efb7afcd7971d1759f4f96e72a100b68bfa960093a61f057da937aa3f"

_ROLE_SCHEMA = {
    "EUR": {
        "ASSET_TOTAL": 1354,
        "LIABILITY_TOTAL": 5850,
        "STATE_COMBINED": 1378,
        "STATE_EXTERNAL": 1377,
        "STATE_INTERNAL": 1376,
    },
    "OTHER": {
        "ASSET_TOTAL": 1432,
        "LIABILITY_TOTAL": 5854,
        "STATE_COMBINED": 1456,
        "STATE_EXTERNAL": 1455,
        "STATE_INTERNAL": 1454,
    },
    "TOTAL": {
        "ASSET_TOTAL": 1458,
        "LIABILITY_TOTAL": 5856,
        "STATE_COMBINED": 1482,
        "STATE_EXTERNAL": 1481,
        "STATE_INTERNAL": 1480,
    },
    "USD": {
        "ASSET_TOTAL": 1380,
        "LIABILITY_TOTAL": 5852,
        "STATE_COMBINED": 1404,
        "STATE_EXTERNAL": 1403,
        "STATE_INTERNAL": 1402,
    },
    "VND": {
        "ASSET_TOTAL": 1406,
        "LIABILITY_TOTAL": 1418,
        "STATE_COMBINED": 1430,
        "STATE_EXTERNAL": 1429,
        "STATE_INTERNAL": 1428,
    },
}
_SCHEMA_EXPECTED = {
    1352: ("Rủi ro tiền tệ", 1259, 1027),
    1354: ("Tổng tài sản", 1353, 1029),
    5850: ("Tổng nợ phải trả", 1366, 1043),
    1376: ("Trạng thái tiền tệ nội bảng", 1353, 1053),
    1377: ("Trạng thái tiền tệ ngoại bảng", 1353, 1054),
    1378: ("Trạng thái tiền tệ nội, ngoại bảng", 1353, 1055),
    1380: ("Tổng tài sản", 1379, 1057),
    5852: ("Tổng nợ phải trả", 1392, 1071),
    1402: ("Trạng thái tiền tệ nội bảng", 1379, 1081),
    1403: ("Trạng thái tiền tệ ngoại bảng", 1379, 1082),
    1404: ("Trạng thái tiền tệ nội, ngoại bảng", 1379, 1083),
    1406: ("Tổng tài sản", 1405, 1085),
    1418: ("Nợ phải trả và vốn chủ sở hữu", 1405, 1097),
    1428: ("Trạng thái tiền tệ nội bảng", 1405, 1107),
    1429: ("Trạng thái tiền tệ ngoại bảng", 1405, 1108),
    1430: ("Trạng thái tiền tệ nội, ngoại bảng", 1405, 1109),
    1432: ("Tổng tài sản", 1431, 1111),
    5854: ("Tổng nợ phải trả", 1444, 1125),
    1454: ("Trạng thái tiền tệ nội bảng", 1431, 1135),
    1455: ("Trạng thái tiền tệ ngoại bảng", 1431, 1136),
    1456: ("Trạng thái tiền tệ nội, ngoại bảng", 1431, 1137),
    1458: ("Tổng tài sản", 1457, 1139),
    5856: ("Tổng nợ phải trả", 1470, 1153),
    1480: ("Trạng thái tiền tệ nội bảng", 1457, 1163),
    1481: ("Trạng thái tiền tệ ngoại bảng", 1457, 1164),
    1482: ("Trạng thái tiền tệ nội, ngoại bảng", 1457, 1165),
}
_CORE_ROLES = {
    "ASSET_TOTAL",
    "LIABILITY_TOTAL",
    "STATE_COMBINED",
    "STATE_EXTERNAL",
    "STATE_INTERNAL",
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_table_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gold_axis_silently_collapsed_into_other_currency": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_accounting_core_cells": True,
    "nonzero_source_presentation_residual_silently_accepted": False,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "row_or_currency_axis_order_required": False,
    "text_similarity_alone_used_for_mapping": False,
    "unsupported_or_uncorroborated_source_cells_discarded": False,
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


class CurrencyRisk8BankCodexVerifiedMappingV1Error(ValueError):
    """The graph, values, equations, schema or result drifted."""


def _error(message: str) -> CurrencyRisk8BankCodexVerifiedMappingV1Error:
    return CurrencyRisk8BankCodexVerifiedMappingV1Error(message)


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    return other._document(items, code, label)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return other._page(document, page, label)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or item.display_order != expected[2]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _period(page: Mapping[str, Any]) -> tuple[str, str, str]:
    text = " ".join(line["vietocr_text_accentless"] for line in page["lines"])
    if re.search(r"31\s+(?:thang\s+)?12(?:\s+nam)?\s+2025", text):
        return "COMPARATIVE", "2025-12-31", "VERIFIED_COMPARATIVE_2025_12_31"
    if re.search(r"31\s+(?:thang\s+)?0?3(?:\s+nam)?\s*2026", text):
        return "CURRENT", "2026-03-31", "VERIFIED_CURRENT_Q1_2026_NOT_Q2"
    if re.search(r"30\s+(?:thang\s+)?0?6(?:\s+nam)?\s*2026", text):
        return "CURRENT", "2026-06-30", "VERIFIED_CURRENT_Q2_2026"
    raise _error("currency-risk table period could not be derived from the bound page")


def _label_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    page_number = event["page_sequence"]
    axis_page = _page(axis_document, page_number, "accounting axis")
    semantic_page = _page(semantic_document, page_number, "semantic index")
    line_index = event["source_line_index"]
    axis_line = axis_page["lines"][line_index]
    semantic_line = semantic_page["lines"][line_index]
    if (
        axis_line["source_line_index"] != line_index
        or semantic_line["source_line_index"] != line_index
        or axis_line["vietocr_text"] != semantic_line["vietocr_text"]
    ):
        raise _error("currency-risk label evidence axis drifted")
    return {
        "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
        "fresh_vietocr_proposal": axis_line["vietocr_text"],
        "line_index": line_index,
        "normalized_fresh_vietocr": axis_line["vietocr_text_accentless"],
        "page_sequence": page_number,
        "source_bbox_raw_pixels": list(axis_line["bbox"]),
    }


def _money(value: Any) -> int:
    if type(value) is not str:
        raise _error("source numeric challenger must be one string")
    try:
        return other.operating.income.foundation.support._money(value)
    except ValueError as exc:
        raise _error(f"source numeric challenger is not monetary: {value!r}") from exc


def _value_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    *,
    axis_role: str,
    line_index: int,
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
    source_text: str,
) -> dict[str, Any]:
    evidence = other._verified_value(
        axis_document,
        semantic_document,
        crop_document,
        {
            "kind": "AUTHENTICATED_LINE",
            "line_index": line_index,
            "page_sequence": page_sequence,
            "pixel_transcription": source_text,
        },
    )
    if evidence["normalized_value"] != _money(source_text):
        raise _error("currency-risk source numeric normalization drifted")
    return {
        **evidence,
        "currency_axis": axis_role,
        "period_axis": period_axis,
        "source_period_date": source_period_date,
    }


def _row_cells(
    page: Mapping[str, Any],
    source_axis: Sequence[Any],
    event: Mapping[str, Any],
) -> list[dict[str, Any]]:
    label = page["lines"][event["source_line_index"]]
    label_y = (label["bbox"][1] + label["bbox"][3]) / 2
    # The label column is not a fixed fraction of the page.  In wide six-axis
    # tables the first monetary column can begin left of the old 48% cutoff.
    # Bind the boundary to the actual row label instead; this remains blind to
    # bank/page identity and lets the authenticated numeric parser reject any
    # non-value neighbour to the right of the label.
    label_zone_limit = label["bbox"][2]
    cells = []
    for line in page["lines"]:
        line_index = line["source_line_index"]
        if line["bbox"][0] <= label_zone_limit:
            continue
        line_y = (line["bbox"][1] + line["bbox"][3]) / 2
        if abs(line_y - label_y) > 27:
            continue
        source_text = source_axis[line_index]
        try:
            normalized_value = _money(source_text)
        except CurrencyRisk8BankCodexVerifiedMappingV1Error:
            continue
        cells.append(
            {
                "center_x": (line["bbox"][0] + line["bbox"][2]) / 2,
                "line_index": line_index,
                "normalized_value": normalized_value,
                "source_text": source_text,
            }
        )
    return sorted(cells, key=lambda item: item["center_x"])


def _parsed_table(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    matcher_page: Mapping[str, Any],
    region: Mapping[str, Any],
    page_sequence: int,
) -> dict[str, Any]:
    matcher = scanner._matcher()
    checked_page = matcher._support()._pages(
        [
            {
                "lines": matcher_page["lines"],
                "page_sequence": 1,
                "primary_numeric_authority": matcher_page["primary_numeric_authority"],
            }
        ]
    )[0]
    axes = matcher._header_features(checked_page)[0]
    if len(axes) < 4 or "USD" not in axes or "TOTAL" not in axes:
        raise _error("currency-risk table axes drifted after graph acceptance")
    axis_page = _page(axis_document, page_sequence, "accounting axis")
    crop_page = _page(crop_document, page_sequence, "crop manifest")
    source_axis = other.operating.income.foundation.support._source_line_axis(crop_page)
    events = [
        event
        for event in region["events"]
        if event["page_sequence"] == page_sequence and event["role"] in _CORE_ROLES
    ]
    if len({event["role"] for event in events}) != len(events) or not {
        "ASSET_TOTAL",
        "LIABILITY_TOTAL",
        "STATE_INTERNAL",
    }.issubset(event["role"] for event in events):
        raise _error("currency-risk core row events drifted")
    cells_by_role = {event["role"]: _row_cells(axis_page, source_axis, event) for event in events}
    full_row = max(cells_by_role.values(), key=len)
    if len(full_row) != len(axes):
        raise _error(
            "currency-risk full row does not bind every observed currency axis: "
            f"page={page_sequence}, axes={axes}, cells={len(full_row)}"
        )
    centers = [cell["center_x"] for cell in full_row]
    minimum_spacing = min(right - left for left, right in zip(centers, centers[1:], strict=False))
    period_axis, source_period_date, period_status = _period(axis_page)
    rows: dict[str, dict[str, Any]] = {}
    for event in events:
        assigned: dict[str, dict[str, Any]] = {}
        for cell in cells_by_role[event["role"]]:
            index = min(range(len(centers)), key=lambda item: abs(centers[item] - cell["center_x"]))
            if abs(centers[index] - cell["center_x"]) > minimum_spacing * 0.48:
                raise _error("currency-risk value cell is outside every currency column")
            axis_role = axes[index]
            if axis_role in assigned:
                raise _error("currency-risk row has duplicate cells in one currency column")
            assigned[axis_role] = _value_evidence(
                axis_document,
                semantic_document,
                crop_document,
                axis_role=axis_role,
                line_index=cell["line_index"],
                page_sequence=page_sequence,
                period_axis=period_axis,
                source_period_date=source_period_date,
                source_text=cell["source_text"],
            )
        rows[event["role"]] = {
            "label_evidence": _label_evidence(axis_document, semantic_document, event),
            "values": assigned,
        }
    return {
        "currency_axes": axes,
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "period_status": period_status,
        "rows": rows,
        "source_period_date": source_period_date,
    }


def _equations(table: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = table["rows"]
    exact = []
    residuals = []
    for axis in table["currency_axes"]:
        internal_roles = ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL")
        if all(axis in rows.get(role, {}).get("values", {}) for role in internal_roles):
            assets = rows["ASSET_TOTAL"]["values"][axis]["normalized_value"]
            liabilities = rows["LIABILITY_TOTAL"]["values"][axis]["normalized_value"]
            visible = rows["STATE_INTERNAL"]["values"][axis]["normalized_value"]
            residual = assets - liabilities - visible
            record = {
                "axis_role": axis,
                "computed_value": assets - liabilities,
                "equation_kind": "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_STATE",
                "page_sequence": table["page_sequence"],
                "period_axis": table["period_axis"],
                "residual": residual,
                "source_period_date": table["source_period_date"],
                "visible_value": visible,
            }
            (exact if residual == 0 else residuals).append(
                {**record, "status": "VERIFIED_EXACT" if residual == 0 else "UNRESOLVED_RESIDUAL"}
            )
        combined_roles = ("STATE_INTERNAL", "STATE_EXTERNAL", "STATE_COMBINED")
        if all(axis in rows.get(role, {}).get("values", {}) for role in combined_roles):
            internal = rows["STATE_INTERNAL"]["values"][axis]["normalized_value"]
            external = rows["STATE_EXTERNAL"]["values"][axis]["normalized_value"]
            visible = rows["STATE_COMBINED"]["values"][axis]["normalized_value"]
            residual = internal + external - visible
            record = {
                "axis_role": axis,
                "computed_value": internal + external,
                "equation_kind": "INTERNAL_STATE_PLUS_EXTERNAL_STATE_EQUALS_COMBINED_STATE",
                "page_sequence": table["page_sequence"],
                "period_axis": table["period_axis"],
                "residual": residual,
                "source_period_date": table["source_period_date"],
                "visible_value": visible,
            }
            (exact if residual == 0 else residuals).append(
                {**record, "status": "VERIFIED_EXACT" if residual == 0 else "UNRESOLVED_RESIDUAL"}
            )
    return exact, residuals


def _eligible_cells(
    table: Mapping[str, Any], exact_equations: Sequence[Mapping[str, Any]]
) -> set[tuple[str, str]]:
    eligible: set[tuple[str, str]] = set()
    for equation in exact_equations:
        axis = equation["axis_role"]
        roles = (
            ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL")
            if equation["equation_kind"].startswith("ASSET_TOTAL")
            else ("STATE_INTERNAL", "STATE_EXTERNAL", "STATE_COMBINED")
        )
        eligible.update((axis, role) for role in roles)
    return eligible


def _trial(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    matcher_pages: Sequence[Mapping[str, Any]],
    schema_by_id: Mapping[int, Any],
    *,
    next_gap_number: int,
) -> tuple[dict[str, Any], int]:
    matcher_result = scan_trial["matcher_result"]
    base = {
        "document_ordinal": scan_trial["document_ordinal"],
        "document_provenance": scan_trial["document_provenance"],
        "source_pdf_sha256": scan_trial["source_pdf_sha256"],
        "whole_document_uniqueness": canonical_clone_v1(matcher_result["uniqueness"]),
    }
    if matcher_result["uniqueness"]["status"] != "UNIQUE_FULL_MATCH":
        return (
            {
                **base,
                "absence_evidence": {
                    "complete_pdf_pages_scanned": True,
                    "near_region_count": matcher_result["metrics"]["near_region_count"],
                    "reason": "NO_COMPLETE_CURRENCY_RISK_TABLE_IN_BOUND_REPORT",
                },
                "source_period_status": "NOT_APPLICABLE",
                "source_presentation_residuals": [],
                "status": "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
                "verified_accounting_equations": [],
                "verified_mappings": [],
                "verified_source_only_rows": [],
            },
            next_gap_number,
        )

    region = matcher_result["regions"][0]
    tables = [
        _parsed_table(
            axis_document,
            semantic_document,
            crop_document,
            matcher_pages[page_sequence - 1],
            region,
            page_sequence,
        )
        for page_sequence in region["table_page_sequences"]
    ]
    exact_equations: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    eligible_by_page: dict[int, set[tuple[str, str]]] = {}
    residual_axes_by_page: dict[int, set[str]] = defaultdict(set)
    for table in tables:
        exact, table_residuals = _equations(table)
        exact_equations.extend(exact)
        residuals.extend(table_residuals)
        eligible_by_page[table["page_sequence"]] = _eligible_cells(table, exact)
        residual_axes_by_page[table["page_sequence"]].update(
            residual["axis_role"] for residual in table_residuals
        )

    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    source_only: dict[tuple[str, str], dict[str, Any]] = {}
    for table in tables:
        page = table["page_sequence"]
        for role, row in table["rows"].items():
            for axis, evidence in row["values"].items():
                reason = None
                if axis == "GOLD":
                    reason = "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"
                elif axis in residual_axes_by_page[page]:
                    reason = "SOURCE_PRESENTATION_ARITHMETIC_RESIDUAL"
                elif (axis, role) not in eligible_by_page[page]:
                    reason = "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"
                target = _ROLE_SCHEMA.get(axis, {}).get(role)
                if target is None:
                    reason = reason or "NO_EQUIVALENT_CORE_SCHEMA_ROW"
                if axis == "VND" and role == "LIABILITY_TOTAL":
                    label = row["label_evidence"]["normalized_fresh_vietocr"]
                    if "von chu so huu" not in label:
                        reason = "VND_SOURCE_TOTAL_EXCLUDES_SCHEMA_PARENT_EQUITY_SCOPE"
                if reason is not None:
                    key = (axis, reason)
                    group = source_only.setdefault(
                        key,
                        {
                            "axis_role": axis,
                            "labels": [],
                            "reason": reason,
                            "status": "UNRESOLVED_SOURCE_ROW_RETAINED",
                            "values": [],
                        },
                    )
                    label_evidence = canonical_clone_v1(row["label_evidence"])
                    if not any(
                        same_typed_json_v1(label_evidence, existing) for existing in group["labels"]
                    ):
                        group["labels"].append(label_evidence)
                    group["values"].append({"source_role": role, **canonical_clone_v1(evidence)})
                    continue
                key = (axis, role)
                mapping = mappings.setdefault(
                    key,
                    {
                        "axis_role": axis,
                        "labels": [],
                        "schema_binding": _schema_binding(schema_by_id[target], target),
                        "source_role": role,
                        "status": "VERIFIED_BY_CODEX",
                        "values": [],
                    },
                )
                label_evidence = canonical_clone_v1(row["label_evidence"])
                if not any(
                    same_typed_json_v1(label_evidence, existing) for existing in mapping["labels"]
                ):
                    mapping["labels"].append(label_evidence)
                mapping["values"].append(canonical_clone_v1(evidence))

    verified_mappings = [mappings[key] for key in sorted(mappings)]
    verified_source_only_rows = []
    for key in sorted(source_only):
        group = source_only[key]
        verified_source_only_rows.append({**group, "gap_id": f"CRISK-{next_gap_number:03d}"})
        next_gap_number += 1
    period_statuses = {table["period_status"] for table in tables}
    source_period_status = (
        "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
        if "VERIFIED_CURRENT_Q1_2026_NOT_Q2" in period_statuses
        else "VERIFIED_CURRENT_Q2_2026_WITH_OPTIONAL_COMPARATIVE_2025_12_31"
    )
    return (
        {
            **base,
            "absence_evidence": None,
            "source_period_status": source_period_status,
            "source_presentation_residuals": residuals,
            "status": (
                "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS"
                if verified_source_only_rows
                else "VERIFIED_BY_CODEX"
            ),
            "verified_accounting_equations": exact_equations,
            "verified_mappings": verified_mappings,
            "verified_source_only_rows": verified_source_only_rows,
        },
        next_gap_number,
    )


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "detailed_table_not_present_document_count": sum(
            trial["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT"
            for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
            for row in group
            for value in row["values"]
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "open_source_group_count": sum(len(trial["verified_source_only_rows"]) for trial in trials),
        "open_source_value_cell_count": sum(
            len(row["values"]) for trial in trials for row in trial["verified_source_only_rows"]
        ),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
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
        raise _error("currency-risk result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "CURRENCY_RISK_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("currency-risk result identity or metrics drifted")
    gap_ids = []
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status")
            not in {
                "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT",
                "VERIFIED_BY_CODEX",
                "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS",
            }
            or any(
                mapping.get("status") != "VERIFIED_BY_CODEX"
                for mapping in trial.get("verified_mappings", [])
            )
            or any(
                row.get("status") != "UNRESOLVED_SOURCE_ROW_RETAINED"
                for row in trial.get("verified_source_only_rows", [])
            )
            or any(
                equation.get("status") != "VERIFIED_EXACT" or equation.get("residual") != 0
                for equation in trial.get("verified_accounting_equations", [])
            )
            or any(
                residual.get("status") != "UNRESOLVED_RESIDUAL" or residual.get("residual") == 0
                for residual in trial.get("source_presentation_residuals", [])
            )
        ):
            raise _error("currency-risk trial shape or status drifted")
        gap_ids.extend(row["gap_id"] for row in trial.get("verified_source_only_rows", []))
    if gap_ids != [f"CRISK-{index:03d}" for index in range(1, len(gap_ids) + 1)]:
        raise _error("currency-risk source gap IDs drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0101:result:" + canonical_json_sha256_v1(material):
        raise _error("currency-risk result identity drifted")
    return canonical_clone_v1(value)


def build_currency_risk_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    scanner.validate_currency_risk_full_document_scan_replay_v1(structure_scan, semantic_index)
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("currency-risk fixed scan ID drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("currency-risk semantic axis drifted")
    schema_family = _schema_binding(schema_by_id[1352], 1352)
    trials = []
    next_gap_number = 1
    for axis_document, semantic_document, crop_document, scan_trial in zip(
        axis["documents"],
        semantic_index["documents"],
        crop_manifest["documents"],
        structure_scan["trials"],
        strict=True,
    ):
        matcher_pages = scanner._support()._matcher_pages(axis_document)
        trial, next_gap_number = _trial(
            axis_document,
            semantic_document,
            crop_document,
            scan_trial,
            matcher_pages,
            schema_by_id,
            next_gap_number=next_gap_number,
        )
        trials.append(trial)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": schema_family,
        "state": "CURRENCY_RISK_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0101:result:" + canonical_json_sha256_v1(material)}
    )


def validate_currency_risk_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_currency_risk_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("currency-risk verified mapping does not replay exactly")
    return supplied


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    payload = other.operating.income.foundation.support._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = other.operating.income.foundation.support._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _live_inputs() -> dict[str, Any]:
    semantic_index, _ = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    structure_scan = scanner.build_live_currency_risk_full_document_scan_v1()
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
    }


def build_live_currency_risk_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_currency_risk_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_currency_risk_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_currency_risk_8bank_codex_verified_mapping_replay_v1(value, **_live_inputs())


def _write(path: Path, value: Any) -> None:
    destination = PROJECT_ROOT / path
    if destination.exists():
        raise _error(f"refusing to overwrite existing currency-risk result: {path}")
    destination.write_bytes(canonical_json_bytes_v1(value) + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.validate_result:
        parser.error("choose exactly one of --write-result or --validate-result")
    if args.write_result:
        _write(RESULT_PATH, build_live_currency_risk_8bank_codex_verified_mapping_v1())
        return
    result, _ = _stable_json(RESULT_PATH)
    validate_live_currency_risk_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
