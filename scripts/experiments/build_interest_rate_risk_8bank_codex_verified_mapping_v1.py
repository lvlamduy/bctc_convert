"""Verify the accounting core of interest-rate-risk tables across eight reports."""

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
        raise RuntimeError(f"cannot load interest-rate-risk support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_interest_rate_risk",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "interest_rate_risk_scan_for_verified_mapping",
    "scan_interest_rate_risk_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "INTEREST_RATE_RISK_8BANK_CODEX_VERIFIED_ACCOUNTING_CORE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_OR_GEOMETRY_SELECTED_ROTATED_"
    "VIETOCR_BANK_BLIND_INTEREST_RATE_RISK_GRAPH_AUTHENTICATED_SOURCE_NUMERIC_"
    "CHALLENGER_GEOMETRIC_COLUMN_ASSIGNMENT_EXACT_ASSET_MINUS_LIABILITY_AND_"
    "INTERNAL_PLUS_EXTERNAL_GAP_EQUATIONS_LIVE_TM_SCHEMA_CORE_ONLY_ROTATED_"
    "NUMERIC_OR_NONCLOSING_CELLS_RETAINED_NO_EXPORT_AUTHORITY"
)
RESULT_PATH = Path(
    "docs/experiments/E-0102-interest-rate-risk-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "irrfdsv1:scan:17fb6e5912ecfa71cd637e06f422fd4e674d90805d85dc64dfd7d1f8f5441e64"

_ROLE_SCHEMA = {
    "NO_INTEREST": {
        "PARENT": 1484,
        "ASSET_TOTAL": 1485,
        "LIABILITY_TOTAL": 1497,
        "STATE_INTERNAL": 1506,
        "STATE_EXTERNAL": 1507,
        "STATE_COMBINED": 1508,
    },
    "OVERDUE": {
        "PARENT": 1509,
        "ASSET_TOTAL": 1510,
        "LIABILITY_TOTAL": 1522,
        "STATE_INTERNAL": 1531,
        "STATE_EXTERNAL": 1532,
        "STATE_COMBINED": 1533,
    },
    "OVERDUE_GT3M": {
        "PARENT": 1534,
        "ASSET_TOTAL": 1535,
        "LIABILITY_TOTAL": 1547,
        "STATE_INTERNAL": 1556,
        "STATE_EXTERNAL": 1557,
        "STATE_COMBINED": 1558,
    },
    "OVERDUE_LE3M": {
        "PARENT": 1559,
        "ASSET_TOTAL": 1560,
        "LIABILITY_TOTAL": 1572,
        "STATE_INTERNAL": 1581,
        "STATE_EXTERNAL": 1582,
        "STATE_COMBINED": 1583,
    },
    "WITHIN_LE1M": {
        "PARENT": 1584,
        "ASSET_TOTAL": 1585,
        "LIABILITY_TOTAL": 1597,
        "STATE_INTERNAL": 1606,
        "STATE_EXTERNAL": 1607,
        "STATE_COMBINED": 1608,
    },
    "WITHIN_1_3M": {
        "PARENT": 1609,
        "ASSET_TOTAL": 1610,
        "LIABILITY_TOTAL": 1622,
        "STATE_INTERNAL": 1631,
        "STATE_EXTERNAL": 1632,
        "STATE_COMBINED": 1633,
    },
    "WITHIN_3_6M": {
        "PARENT": 1634,
        "ASSET_TOTAL": 1635,
        "LIABILITY_TOTAL": 1647,
        "STATE_INTERNAL": 1656,
        "STATE_EXTERNAL": 1657,
        "STATE_COMBINED": 1658,
    },
    "WITHIN_6_12M": {
        "PARENT": 1659,
        "ASSET_TOTAL": 1660,
        "LIABILITY_TOTAL": 1672,
        "STATE_INTERNAL": 1681,
        "STATE_EXTERNAL": 1682,
        "STATE_COMBINED": 1683,
    },
    "WITHIN_1_5Y": {
        "PARENT": 1684,
        "ASSET_TOTAL": 1685,
        "LIABILITY_TOTAL": 1697,
        "STATE_INTERNAL": 1706,
        "STATE_EXTERNAL": 1707,
        "STATE_COMBINED": 1708,
    },
    "WITHIN_GT5Y": {
        "PARENT": 1709,
        "ASSET_TOTAL": 1710,
        "LIABILITY_TOTAL": 1722,
        "STATE_INTERNAL": 1731,
        "STATE_EXTERNAL": 1732,
        "STATE_COMBINED": 1733,
    },
    "WITHIN_GT1Y": {
        "PARENT": 5869,
        "ASSET_TOTAL": 5870,
        "LIABILITY_TOTAL": 5884,
        "STATE_INTERNAL": 5893,
        "STATE_EXTERNAL": 5894,
        "STATE_COMBINED": 5895,
    },
    "TOTAL": {
        "PARENT": 1734,
        "ASSET_TOTAL": 1735,
        "LIABILITY_TOTAL": 1747,
        "STATE_INTERNAL": 1756,
        "STATE_EXTERNAL": 1757,
        "STATE_COMBINED": 1758,
    },
}
_EXPECTED_ROLE_NAMES = {
    "ASSET_TOTAL": "Tổng Tài sản",
    "LIABILITY_TOTAL": "Tổng Nợ phải trả",
    "STATE_INTERNAL": "Chênh lệch nhạy cảm với lãi suất nội bảng",
    "STATE_EXTERNAL": "Chênh lệch nhạy cảm với lãi suất ngoại bảng",
    "STATE_COMBINED": "Chênh lệch nhạy cảm với lãi suất nội, ngoại bảng",
}
_CORE_ROLES = set(_EXPECTED_ROLE_NAMES)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "detailed_table_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_exact_accounting_core_cells": True,
    "nonzero_source_presentation_residual_silently_accepted": False,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "repricing_axis_or_row_order_required": False,
    "rotated_source_numeric_axis_promoted_without_independent_challenger": False,
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


class InterestRateRisk8BankCodexVerifiedMappingV1Error(ValueError):
    """The graph, values, equations, schema or result drifted."""


def _error(message: str) -> InterestRateRisk8BankCodexVerifiedMappingV1Error:
    return InterestRateRisk8BankCodexVerifiedMappingV1Error(message)


def _page(document: Mapping[str, Any], page: int, label: str) -> dict[str, Any]:
    return other._page(document, page, label)


def _schema_family(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != 1483
        or item.canonical_name != "Rủi ro lãi suất"
        or item.parent_id != 1259
        or item.display_order != 1166
    ):
        raise _error("interest-rate-risk family does not bind exact live TM schema root")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _schema_binding(item: Any, axis: str, role: str) -> dict[str, Any]:
    axis_schema = _ROLE_SCHEMA.get(axis)
    report_norm_id = axis_schema.get(role) if axis_schema is not None else None
    expected_parent = axis_schema.get("PARENT") if axis_schema is not None else None
    if (
        item is None
        or report_norm_id is None
        or role not in _EXPECTED_ROLE_NAMES
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != _EXPECTED_ROLE_NAMES[role]
        or item.parent_id != expected_parent
        or type(item.display_order) is not int
    ):
        raise _error(f"mapping does not bind exact live interest-rate TM row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _money(value: Any) -> int:
    if type(value) is not str:
        raise _error("source numeric challenger must be one string")
    try:
        return other.operating.income.foundation.support._money(value)
    except ValueError as exc:
        raise _error(f"source numeric challenger is not monetary: {value!r}") from exc


def _period(page: Mapping[str, Any]) -> tuple[str, str, str]:
    dated_lines = []
    for line in page["lines"]:
        value = line["normalized_text"]
        period = None
        if re.search(r"31\s+(?:thang\s+)?0?3(?:\s+nam)?\s*2026", value):
            period = ("CURRENT", "2026-03-31", "VERIFIED_CURRENT_Q1_2026_NOT_Q2")
        elif re.search(r"30\s+(?:thang\s+)?0?6(?:\s+nam)?\s*2026", value):
            period = ("CURRENT", "2026-06-30", "VERIFIED_CURRENT_Q2_2026")
        elif re.search(r"31\s+(?:thang\s+)?12(?:\s+nam)?\s+2025", value):
            period = ("COMPARATIVE", "2025-12-31", "VERIFIED_COMPARATIVE_2025_12_31")
        if period is not None:
            dated_lines.append((line["bbox"][1], period))
    if dated_lines:
        return max(dated_lines, key=lambda item: item[0])[1]
    text = " ".join(line["normalized_text"] for line in page["lines"])
    if re.search(r"31\s+(?:thang\s+)?0?3(?:\s+nam)?\s*2026", text):
        return "CURRENT", "2026-03-31", "VERIFIED_CURRENT_Q1_2026_NOT_Q2"
    if re.search(r"30\s+(?:thang\s+)?0?6(?:\s+nam)?\s*2026", text):
        return "CURRENT", "2026-06-30", "VERIFIED_CURRENT_Q2_2026"
    if re.search(r"31\s+(?:thang\s+)?12(?:\s+nam)?\s+2025", text):
        return "COMPARATIVE", "2025-12-31", "VERIFIED_COMPARATIVE_2025_12_31"
    raise _error("interest-rate-risk table period could not be derived from the bound page")


def _label_spans(page: Mapping[str, Any], matcher: ModuleType) -> dict[str, dict[str, Any]]:
    support = matcher._support()
    label_limit = max(line["bbox"][2] for line in page["lines"]) * 0.46
    labels = [
        line
        for line in page["lines"]
        if line["bbox"][0] <= label_limit
        and support._NUMBER.fullmatch(line["normalized_text"]) is None
        and line["normalized_text"] not in {"", "-", "--"}
        and re.fullmatch(r"[ivx]+", line["normalized_text"]) is None
    ]
    candidates: list[dict[str, Any]] = []
    for index, line in enumerate(labels):
        parts = [line]
        role = matcher._raw_role(line["normalized_text"])
        quality = 2 if role is not None else 0
        phrase = line["normalized_text"]
        explored = [line]
        for following in labels[index + 1 : index + 3] if role in {None, "STATE_INTERNAL"} else []:
            if following["bbox"][1] - line["bbox"][3] > 100:
                break
            explored.append(following)
            combined_phrase = phrase + " " + following["normalized_text"]
            combined_role = matcher._raw_role(combined_phrase)
            if combined_role == "STATE_COMBINED" and role != "STATE_COMBINED":
                parts = list(explored)
                role = combined_role
                quality = 2
                break
            if role is None and combined_role is not None:
                parts = list(explored)
                role = combined_role
                quality = 1
                break
            phrase = combined_phrase
        if role is None:
            continue
        candidates.append(
            {
                "parts": parts,
                "quality": quality,
                "raw_role": role,
                "x1": min(part["bbox"][0] for part in parts),
                "x2": max(part["bbox"][2] for part in parts),
                "y1": min(part["bbox"][1] for part in parts),
                "y2": max(part["bbox"][3] for part in parts),
            }
        )
    asset_total_y = min(
        (item["y1"] for item in candidates if item["raw_role"] == "ASSET_TOTAL"),
        default=None,
    )
    if asset_total_y is None:
        raise _error("interest-rate-risk table has no geometric asset-total boundary")
    best: dict[str, dict[str, Any]] = {}
    for item in candidates:
        role = item.pop("raw_role")
        if role == "DERIVATIVE_ROW":
            role = "LIABILITY_DERIVATIVE" if item["y1"] > asset_total_y else "ASSET_DERIVATIVE"
        elif role == "INTERBANK_ROW":
            role = (
                "LIABILITY_GOVERNMENT_INTERBANK"
                if item["y1"] > asset_total_y
                else "ASSET_INTERBANK"
            )
        rank = (item["quality"], -len(item["parts"]), -item["y1"])
        previous = best.get(role)
        if previous is None or rank > previous["rank"]:
            best[role] = {**item, "rank": rank, "role": role}
    return best


def _label_evidence(
    semantic_document: Mapping[str, Any], span: Mapping[str, Any], page_sequence: int
) -> dict[str, Any]:
    semantic_page = _page(semantic_document, page_sequence, "semantic index")
    components = []
    for line in span["parts"]:
        source_index = line["source_line_index"]
        semantic_line = semantic_page["lines"][source_index]
        if semantic_line["source_line_index"] != source_index:
            raise _error("interest-rate-risk label semantic line axis drifted")
        components.append(
            {
                "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
                "fresh_vietocr_proposal": line["vietocr_text"],
                "line_index": source_index,
                "page_sequence": page_sequence,
                "semantic_text_source": line["semantic_text_source"],
                "source_bbox_raw_pixels": list(line["bbox"]),
            }
        )
    return {
        "components": components,
        "normalized_fresh_vietocr": " ".join(line["normalized_text"] for line in span["parts"]),
    }


def _clusters(cells: Sequence[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for cell in sorted(cells, key=lambda item: item["center_y"]):
        if (
            not groups
            or abs(cell["center_y"] - sum(x["center_y"] for x in groups[-1]) / len(groups[-1])) > 14
        ):
            groups.append([dict(cell)])
        else:
            groups[-1].append(dict(cell))
    return groups


def _row_cells(
    page: Mapping[str, Any],
    source_axis: Sequence[Any],
    span: Mapping[str, Any],
    axis_centers: Sequence[tuple[str, float]],
) -> dict[str, dict[str, Any]]:
    candidates = []
    for line in page["lines"]:
        if line["bbox"][0] <= span["x2"]:
            continue
        source_index = line["source_line_index"]
        source_text = source_axis[source_index]
        try:
            normalized_value = _money(source_text)
        except InterestRateRisk8BankCodexVerifiedMappingV1Error:
            continue
        candidates.append(
            {
                "center_x": (line["bbox"][0] + line["bbox"][2]) / 2,
                "center_y": (line["bbox"][1] + line["bbox"][3]) / 2,
                "line": line,
                "normalized_value": normalized_value,
                "source_text": source_text,
            }
        )
    margin = max(18.0, (span["y2"] - span["y1"]) * 0.35)
    groups = [
        group
        for group in _clusters(candidates)
        if span["y1"] - margin
        <= sum(cell["center_y"] for cell in group) / len(group)
        <= span["y2"] + margin
    ]
    if not groups:
        return {}
    label_center = (span["y1"] + span["y2"]) / 2
    maximum_count = max(len(group) for group in groups)
    viable = [group for group in groups if len(group) >= maximum_count - 1]
    selected = min(
        viable,
        key=lambda group: (
            abs(sum(cell["center_y"] for cell in group) / len(group) - label_center),
            -len(group),
        ),
    )
    centers = [center for _axis, center in axis_centers]
    if len(centers) < 2:
        raise _error("interest-rate-risk table has too few geometric axes")
    minimum_spacing = min(right - left for left, right in zip(centers, centers[1:], strict=False))
    assigned: dict[str, dict[str, Any]] = {}
    for cell in selected:
        index = min(range(len(centers)), key=lambda item: abs(centers[item] - cell["center_x"]))
        if abs(centers[index] - cell["center_x"]) > minimum_spacing * 0.48:
            raise _error(
                "interest-rate-risk value is outside every repricing column: "
                f"role={span['role']}, source_line={cell['line']['source_line_index']}, "
                f"x={cell['center_x']}, nearest={centers[index]}"
            )
        axis = axis_centers[index][0]
        if axis in assigned:
            raise _error("interest-rate-risk row repeats one repricing column")
        assigned[axis] = cell
    return assigned


def _value_evidence(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    *,
    axis_role: str,
    cell: Mapping[str, Any],
    page_sequence: int,
    period_axis: str,
    source_period_date: str,
) -> dict[str, Any]:
    source_index = cell["line"]["source_line_index"]
    evidence = other._verified_value(
        axis_document,
        semantic_document,
        crop_document,
        {
            "kind": "AUTHENTICATED_LINE",
            "line_index": source_index,
            "page_sequence": page_sequence,
            "pixel_transcription": cell["source_text"],
        },
    )
    if evidence["normalized_value"] != cell["normalized_value"]:
        raise _error("interest-rate-risk source numeric normalization drifted")
    proposal = cell["line"]["vietocr_text"]
    try:
        proposal_value = _money(proposal)
    except InterestRateRisk8BankCodexVerifiedMappingV1Error:
        proposal_value = None
    return {
        **evidence,
        "fresh_vietocr_numeric_proposal": proposal,
        "fresh_vietocr_numeric_status": (
            "MATCHES_SOURCE_NUMERIC_CHALLENGER"
            if proposal_value == evidence["normalized_value"]
            else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
        ),
        "fresh_vietocr_semantic_text_source": cell["line"]["semantic_text_source"],
        "period_axis": period_axis,
        "repricing_axis": axis_role,
        "source_period_date": source_period_date,
    }


def _parsed_table(
    axis_document: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    matcher_page: Mapping[str, Any],
    page_sequence: int,
    previous_matcher_page: Mapping[str, Any] | None,
    document_matcher_pages: Sequence[Mapping[str, Any]],
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
    axes, axis_events, _unit_count = matcher._header_features(checked_page)
    axis_event_by_role = {
        event["role"].removeprefix("REPRICING_AXIS_"): event
        for event in axis_events
        if event["role"].startswith("REPRICING_AXIS_")
    }
    if set(axis_event_by_role) != set(axes):
        raise _error("interest-rate-risk header geometry or axis roles drifted")
    axis_centers = [
        (
            axis,
            (axis_event_by_role[axis]["bbox"][0] + axis_event_by_role[axis]["bbox"][2]) / 2,
        )
        for axis in axes
    ]
    spans = _label_spans(checked_page, matcher)
    if not {"ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL"} <= set(spans):
        raise _error("interest-rate-risk table lost one required core row")
    crop_page = _page(crop_document, page_sequence, "crop manifest")
    source_axis = other.operating.income.foundation.support._source_line_axis(crop_page)
    try:
        period_axis, source_period_date, period_status = _period(checked_page)
    except InterestRateRisk8BankCodexVerifiedMappingV1Error:
        if previous_matcher_page is None:
            raise
        checked_previous = matcher._support()._pages(
            [
                {
                    "lines": previous_matcher_page["lines"],
                    "page_sequence": 1,
                    "primary_numeric_authority": previous_matcher_page["primary_numeric_authority"],
                }
            ]
        )[0]
        try:
            period_axis, source_period_date, period_status = _period(checked_previous)
        except InterestRateRisk8BankCodexVerifiedMappingV1Error:
            for context_page in document_matcher_pages[:5]:
                checked_context = matcher._support()._pages(
                    [
                        {
                            "lines": context_page["lines"],
                            "page_sequence": 1,
                            "primary_numeric_authority": context_page["primary_numeric_authority"],
                        }
                    ]
                )[0]
                try:
                    period_axis, source_period_date, period_status = _period(checked_context)
                    break
                except InterestRateRisk8BankCodexVerifiedMappingV1Error:
                    continue
            else:
                raise
    rows = {}
    for role in _CORE_ROLES:
        span = spans.get(role)
        if span is None:
            continue
        assigned = _row_cells(checked_page, source_axis, span, axis_centers)
        rows[role] = {
            "label_evidence": _label_evidence(semantic_document, span, page_sequence),
            "values": {
                axis: _value_evidence(
                    axis_document,
                    semantic_document,
                    crop_document,
                    axis_role=axis,
                    cell=cell,
                    page_sequence=page_sequence,
                    period_axis=period_axis,
                    source_period_date=source_period_date,
                )
                for axis, cell in assigned.items()
            },
        }
    return {
        "page_sequence": page_sequence,
        "period_axis": period_axis,
        "period_status": period_status,
        "repricing_axes": axes,
        "rows": rows,
        "source_period_date": source_period_date,
    }


def _equations(table: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = table["rows"]
    exact = []
    residuals = []
    for axis in table["repricing_axes"]:
        for kind, roles, operator in (
            (
                "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_GAP",
                ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL"),
                "SUBTRACT",
            ),
            (
                "INTERNAL_GAP_PLUS_EXTERNAL_GAP_EQUALS_COMBINED_GAP",
                ("STATE_INTERNAL", "STATE_EXTERNAL", "STATE_COMBINED"),
                "ADD",
            ),
        ):
            if not all(axis in rows.get(role, {}).get("values", {}) for role in roles):
                continue
            left = rows[roles[0]]["values"][axis]["normalized_value"]
            right = rows[roles[1]]["values"][axis]["normalized_value"]
            visible = rows[roles[2]]["values"][axis]["normalized_value"]
            computed = left - right if operator == "SUBTRACT" else left + right
            residual = computed - visible
            record = {
                "computed_value": computed,
                "equation_kind": kind,
                "page_sequence": table["page_sequence"],
                "period_axis": table["period_axis"],
                "repricing_axis": axis,
                "residual": residual,
                "source_period_date": table["source_period_date"],
                "visible_value": visible,
            }
            target = exact if residual == 0 else residuals
            target.append(
                {
                    **record,
                    "status": "VERIFIED_EXACT" if residual == 0 else "UNRESOLVED_RESIDUAL",
                }
            )
    return exact, residuals


def _eligible_cells(
    equations: Sequence[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    eligible: set[tuple[str, str]] = set()
    for equation in equations:
        roles = (
            ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL")
            if equation["equation_kind"].startswith("ASSET_TOTAL")
            else ("STATE_INTERNAL", "STATE_EXTERNAL", "STATE_COMBINED")
        )
        eligible.update((equation["repricing_axis"], role) for role in roles)
    return eligible


def _label_evidence_sort_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    components = value["components"]
    return (
        tuple((component["page_sequence"], component["line_index"]) for component in components),
        value["normalized_fresh_vietocr"],
    )


def _value_evidence_sort_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        value["page_sequence"],
        value["source_line_index"],
        value.get("source_role", ""),
        value["period_axis"],
    )


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
        "rotated_rescue_line_count": scan_trial["rotated_rescue_line_count"],
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
                    "reason": "NO_COMPLETE_INTEREST_RATE_RISK_TABLE_IN_BOUND_REPORT",
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
            page_sequence,
            matcher_pages[page_sequence - 2] if page_sequence > 1 else None,
            matcher_pages,
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
        eligible_by_page[table["page_sequence"]] = _eligible_cells(exact)
        residual_axes_by_page[table["page_sequence"]].update(
            residual["repricing_axis"] for residual in table_residuals
        )
    mappings: dict[tuple[str, str], dict[str, Any]] = {}
    source_only: dict[tuple[str, str], dict[str, Any]] = {}
    rotated_numeric = scan_trial["rotated_rescue_line_count"] > 0
    for table in tables:
        page = table["page_sequence"]
        for role, row in table["rows"].items():
            for axis, evidence in row["values"].items():
                reason = None
                if rotated_numeric:
                    reason = "ROTATED_SOURCE_NUMERIC_AXIS_REQUIRES_INDEPENDENT_CHALLENGER"
                elif axis in residual_axes_by_page[page]:
                    reason = "SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL"
                elif (axis, role) not in eligible_by_page[page]:
                    reason = "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"
                target = _ROLE_SCHEMA.get(axis, {}).get(role)
                if target is None:
                    reason = reason or "NO_EQUIVALENT_CORE_SCHEMA_ROW"
                if reason is not None:
                    key = (axis, reason)
                    group = source_only.setdefault(
                        key,
                        {
                            "labels": [],
                            "reason": reason,
                            "repricing_axis": axis,
                            "status": "UNRESOLVED_SOURCE_ROW_RETAINED",
                            "values": [],
                        },
                    )
                    label = canonical_clone_v1(row["label_evidence"])
                    if not any(same_typed_json_v1(label, old) for old in group["labels"]):
                        group["labels"].append(label)
                    group["values"].append({"source_role": role, **canonical_clone_v1(evidence)})
                    continue
                key = (axis, role)
                mapping = mappings.setdefault(
                    key,
                    {
                        "labels": [],
                        "repricing_axis": axis,
                        "schema_binding": _schema_binding(schema_by_id[target], axis, role),
                        "source_role": role,
                        "status": "VERIFIED_BY_CODEX",
                        "values": [],
                    },
                )
                label = canonical_clone_v1(row["label_evidence"])
                if not any(same_typed_json_v1(label, old) for old in mapping["labels"]):
                    mapping["labels"].append(label)
                mapping["values"].append(canonical_clone_v1(evidence))
    verified_mappings = []
    for key in sorted(mappings):
        mapping = mappings[key]
        mapping["labels"].sort(key=_label_evidence_sort_key)
        mapping["values"].sort(key=_value_evidence_sort_key)
        verified_mappings.append(mapping)
    verified_source_only_rows = []
    for key in sorted(source_only):
        group = source_only[key]
        group["labels"].sort(key=_label_evidence_sort_key)
        group["values"].sort(key=_value_evidence_sort_key)
        verified_source_only_rows.append({**group, "gap_id": f"IRISK-{next_gap_number:03d}"})
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
                "UNRESOLVED_WITH_RETAINED_SOURCE_GAPS"
                if not verified_mappings
                else (
                    "VERIFIED_BY_CODEX_WITH_RETAINED_SOURCE_GAPS"
                    if verified_source_only_rows
                    else "VERIFIED_BY_CODEX"
                )
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
        "rotated_numeric_unresolved_document_count": sum(
            trial["rotated_rescue_line_count"] > 0
            and trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
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
        raise _error("interest-rate-risk result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "INTEREST_RATE_RISK_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("interest-rate-risk result identity or metrics drifted")
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
                "UNRESOLVED_WITH_RETAINED_SOURCE_GAPS",
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
            raise _error("interest-rate-risk trial shape or status drifted")
        gap_ids.extend(row["gap_id"] for row in trial.get("verified_source_only_rows", []))
    if gap_ids != [f"IRISK-{index:03d}" for index in range(1, len(gap_ids) + 1)]:
        raise _error("interest-rate-risk source gap IDs drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0102:result:" + canonical_json_sha256_v1(material):
        raise _error("interest-rate-risk result identity drifted")
    return canonical_clone_v1(value)


def build_interest_rate_risk_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    rescue: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    scanner.validate_interest_rate_risk_full_document_scan_replay_v1(
        structure_scan, semantic_index, rescue
    )
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("interest-rate-risk fixed scan ID drifted")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("interest-rate-risk semantic axis drifted")
    rescue_checked = scanner._support()._validate_rescue(rescue)
    rescue_by_locator = {
        (
            sample["document_ordinal"],
            sample["physical_page"],
            sample["source_line_index"],
        ): sample
        for sample in rescue_checked["samples"]
    }
    trials = []
    next_gap_number = 1
    for axis_document, semantic_document, crop_document, scan_trial in zip(
        axis["documents"],
        semantic_index["documents"],
        crop_manifest["documents"],
        structure_scan["trials"],
        strict=True,
    ):
        matcher_pages, applied = scanner._support()._matcher_pages(axis_document, rescue_by_locator)
        if applied != scan_trial["rotated_rescue_line_count"]:
            raise _error("interest-rate-risk rotated rescue trial binding drifted")
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
            "rotated_rescue_projection_id": rescue_checked["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": _schema_family(schema_by_id[1483]),
        "state": "INTEREST_RATE_RISK_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0102:result:" + canonical_json_sha256_v1(material)}
    )


def validate_interest_rate_risk_8bank_codex_verified_mapping_replay_v1(
    value: Any,
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    rescue: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_interest_rate_risk_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        rescue,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_manifest_sha256,
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("interest-rate-risk verified mapping does not replay exactly")
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
    support = scanner._support()
    rescue = support._rescue_builder().read_verified_full_document_rotated_vietocr_rescue_v1()
    structure_scan = scanner.build_interest_rate_risk_full_document_scan_v1(semantic_index, rescue)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "rescue": rescue,
        "schema_authority": schema_authority,
        "schema_by_id": schema_by_id,
        "semantic_index": semantic_index,
        "structure_scan": structure_scan,
    }


def build_live_interest_rate_risk_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_interest_rate_risk_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_interest_rate_risk_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    return validate_interest_rate_risk_8bank_codex_verified_mapping_replay_v1(
        value, **_live_inputs()
    )


def _write(path: Path, value: Any) -> None:
    destination = PROJECT_ROOT / path
    if destination.exists():
        raise _error(f"refusing to overwrite existing interest-rate-risk result: {path}")
    destination.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.validate_result:
        parser.error("choose exactly one of --write-result or --validate-result")
    if args.write_result:
        _write(RESULT_PATH, build_live_interest_rate_risk_8bank_codex_verified_mapping_v1())
        return
    result, _ = _stable_json(RESULT_PATH)
    validate_live_interest_rate_risk_8bank_codex_verified_mapping_v1(result)


if __name__ == "__main__":
    main()
