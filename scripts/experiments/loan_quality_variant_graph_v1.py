"""Bank-blind variant graph for five-grade customer-loan quality tables.

This family wrapper deliberately has no bank, filename, note, or page routing.
It scans one complete PDF with fresh VietOCR Transformer text, enumerates every
complete/near structural region through the shared accounting variant engine,
and then checks geometry, period/unit axes, optional rows, totals, and additive
accounting relationships.

Two presentation families are supported by the same rules:

* horizontal two-period (or money/percent) tables;
* repeated period blocks with several asset columns, where the customer-loan
  column is selected from its geometric header rather than a fixed position.

An optional row containing ``Trong đó`` is retained as non-additive evidence.
A margin/advance row after the five grades is retained as an additive child.
Neither is silently folded into a grade.  Text is anchor evidence only.  A row
can receive numeric authority only from the exact bound source surface, and no
row receives schema-mapping authority in this module.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    center_x2_v1,
    extract_period_axis_v1,
    extract_typed_value_vector_v1,
    is_number_like_v1,
    money_values_v1,
    percentage_values_v1,
    unit_kind_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    build_accounting_variant_region_scan_v1,
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanQualityVariantGraphV1Error",
    "build_loan_quality_variant_graph_document_v1",
    "validate_loan_quality_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_QUALITY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_QUALITY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_LOAN_QUALITY_STRUCTURE_GEOMETRY_"
    "PERIOD_UNIT_TOTAL_AND_ACCOUNTING_CORROBORATION_ONLY_TEXT_IS_ANCHOR_"
    "NO_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")
_MAX_ROLE_ANCHOR_LINE_SPAN = 3
_ROLE_ALIASES = {
    "STANDARD": (
        "Nợ đủ tiêu chuẩn",
        "Nhóm 1 Nợ đủ tiêu chuẩn",
        "Nợ nhóm 1",
    ),
    "SPECIAL_MENTION": (
        "Nợ cần chú ý",
        "Nhóm 2 Nợ cần chú ý",
        "Nợ nhóm 2",
    ),
    "SUBSTANDARD": (
        "Nợ dưới tiêu chuẩn",
        "Nhóm 3 Nợ dưới tiêu chuẩn",
        "Nợ nhóm 3",
    ),
    "DOUBTFUL": (
        "Nợ nghi ngờ",
        "Nhóm 4 Nợ nghi ngờ",
        "Nợ nhóm 4",
    ),
    "LOSS": (
        "Nợ có khả năng mất vốn",
        "Nhóm 5 Nợ có khả năng mất vốn",
        "Nợ nhóm 5",
    ),
}
_ENGINE_SPEC = {
    "branch_core_phrases": ["phân"],
    "branch_variants": [
        {
            "anchor_phrase": "tích chất lượng nợ cho vay",
            "variant_id": "LOAN_QUALITY_WORDING",
        },
        {
            "anchor_phrase": "tích chất lượng dư nợ cho vay khách hàng",
            "variant_id": "CUSTOMER_LOAN_QUALITY_WORDING",
        },
        {
            "anchor_phrase": "tích dư nợ cho vay theo chất lượng nợ",
            "variant_id": "DEBT_BY_QUALITY_WORDING",
        },
        {
            "anchor_phrase": "loại chất lượng tài sản có rủi ro tín dụng",
            "allow_inline_prefix": True,
            "variant_id": "CREDIT_RISK_ASSET_QUALITY_WORDING",
        },
    ],
    "family_id": FAMILY_ID,
    "format_version": "ACCOUNTING_VARIANT_FAMILY_SPEC_V1",
    "limits": {
        "max_branch_to_last_child_line_span": 64,
        "max_child_gap": 18,
        "min_numeric_followers_per_child": 2,
    },
    "optional_intermediate_aliases": [
        "Dư nợ cho vay",
        "Dư nợ cho vay khách hàng",
    ],
    "ordered_children": [{"aliases": list(_ROLE_ALIASES[role]), "role": role} for role in _ROLES],
    "owner_aliases": [
        "Cho vay khách hàng",
        "Dư nợ cho vay khách hàng",
        "Các khoản cho vay khách hàng",
        "Rủi ro tín dụng",
    ],
}
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "blank_companion_cells_imputed_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "legacy_ocr_used_for_semantic_anchors": False,
    "mapping_authority": False,
    "near_regions_preserved": True,
    "nonadditive_rows_silently_added": False,
    "numeric_authority_requires_bound_source_surface": True,
    "percentage_or_companion_columns_silently_discarded": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "qwen_challenger_used_for_semantic_anchors": False,
    "text_similarity_alone_can_accept": False,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "graphs",
    "metrics",
    "region_scan",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_SECTION_NUMBER = re.compile(r"^\d{1,3}(?:\.\d{1,2}){1,2}\.?$", re.ASCII)


class LoanQualityVariantGraphV1Error(ValueError):
    """The full-document line axis, family graph, or replay drifted."""


def _error(message: str) -> LoanQualityVariantGraphV1Error:
    return LoanQualityVariantGraphV1Error(message)


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _pages(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("loan-quality scan requires one non-empty complete PDF page sequence")
    pages: list[dict[str, Any]] = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error(f"loan-quality page {page_offset} fields drifted")
        if type(raw_page["page_sequence"]) is not int or raw_page["page_sequence"] <= 0:
            raise _error("loan-quality page sequence drifted")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("loan-quality numeric authority flag drifted")
        if type(raw_page["lines"]) is not list:
            raise _error("loan-quality line axis drifted")
        lines: list[dict[str, Any]] = []
        for line_offset, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-quality semantic line fields drifted")
            if (
                type(raw_line["source_line_index"]) is not int
                or raw_line["source_line_index"] != line_offset
                or type(raw_line["vietocr_text"]) is not str
                or (
                    raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str
                )
            ):
                raise _error("loan-quality semantic line identity/text drifted")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], "loan-quality semantic line"),
                    "source_line_index": line_offset,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
        pages.append(
            {
                "lines": lines,
                "page_sequence": raw_page["page_sequence"],
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
    sequences = [page["page_sequence"] for page in pages]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise _error("loan-quality document pages must be unique and ordered")
    return pages


def _engine_scan(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return build_accounting_variant_region_scan_v1(
        [
            {
                "lines": [
                    {
                        "source_line_index": line["source_line_index"],
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in page["lines"]
                ],
                "page_sequence": page["page_sequence"],
            }
            for page in pages
        ],
        _ENGINE_SPEC,
    )


def _page_by_sequence(pages: Sequence[Mapping[str, Any]], page_sequence: int) -> Mapping[str, Any]:
    return next(page for page in pages if page["page_sequence"] == page_sequence)


def _numeric_runs(lines: Sequence[Mapping[str, Any]]) -> list[list[Mapping[str, Any]]]:
    runs: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    for line in lines:
        if is_number_like_v1(line["vietocr_text"]):
            current.append(line)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _immediate_numeric_run(
    lines: Sequence[Mapping[str, Any]], start: int, stop: int
) -> tuple[list[Mapping[str, Any]], int]:
    cursor = start
    while cursor < stop and not is_number_like_v1(lines[cursor]["vietocr_text"]):
        cursor += 1
    run: list[Mapping[str, Any]] = []
    while cursor < stop and is_number_like_v1(lines[cursor]["vietocr_text"]):
        if run:
            if center_x2_v1(lines[cursor]) <= center_x2_v1(run[-1]):
                break
            previous_box = run[-1]["bbox"]
            current_box = lines[cursor]["bbox"]
            previous_height = previous_box[3] - previous_box[1]
            current_height = current_box[3] - current_box[1]
            if current_box[1] - previous_box[3] > max(48, 3 * max(previous_height, current_height)):
                break
        run.append(lines[cursor])
        cursor += 1
    return run, cursor


def _inherited_document_unit(
    pages: Sequence[Mapping[str, Any]],
    target_page: int,
    before_source_line_index: int,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        if page["page_sequence"] > target_page:
            break
        for line in page["lines"]:
            if (
                page["page_sequence"] == target_page
                and line["source_line_index"] >= before_source_line_index
            ):
                continue
            normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
            if unit_kind_v1(line["vietocr_text"]) == "MONEY" and "don vi" in normalized:
                candidates.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["source_line_index"],
                        "surface": line["vietocr_text"],
                    }
                )
    return candidates[-1] if candidates else None


def _lane_axis(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    header: Sequence[Mapping[str, Any]],
    inferred_count: int,
    branch_source_line_index: int,
) -> tuple[list[str], dict[str, Any], list[str]]:
    reasons: list[str] = []
    local = [
        {
            "kind": kind,
            "source_line_index": line["source_line_index"],
            "surface": line["vietocr_text"],
            "x_center_x2": center_x2_v1(line),
        }
        for line in header
        if (kind := unit_kind_v1(line["vietocr_text"])) is not None
    ]
    local.sort(key=lambda item: item["x_center_x2"])
    if len(local) == inferred_count:
        lane_types = [item["kind"] for item in local]
        scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [item["source_line_index"] for item in local],
            "surfaces": [item["surface"] for item in local],
        }
    elif len(local) == 1 and local[0]["kind"] == "MONEY" and inferred_count >= 2:
        lane_types = ["MONEY"] * inferred_count
        scope = {
            "mode": "LOCAL_SHARED_MONEY_UNIT",
            "source_line_indices": [local[0]["source_line_index"]],
            "surfaces": [local[0]["surface"]],
        }
    elif not local:
        inherited = _inherited_document_unit(pages, page["page_sequence"], branch_source_line_index)
        if inherited is None:
            lane_types = ["MONEY", "MONEY"] if inferred_count == 2 else []
            scope = {"mode": "UNRESOLVED"}
            reasons.append("UNIT_SCOPE_NOT_RESOLVED")
        else:
            lane_types = ["MONEY"] * inferred_count
            scope = {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}
    else:
        lane_types = []
        scope = {
            "mode": "UNRESOLVED_LOCAL_UNIT_COUNT_MISMATCH",
            "local_unit_count": len(local),
        }
        reasons.append("TYPED_LANE_AXIS_NOT_RESOLVED")
    if (
        lane_types
        and lane_types
        not in (
            ["MONEY", "MONEY"],
            ["MONEY", "PERCENT", "MONEY", "PERCENT"],
        )
        and inferred_count <= 4
    ):
        reasons.append("SUPPORTED_TYPED_LANE_LAYOUT_NOT_RESOLVED")
    return lane_types, scope, reasons


def _role_groups(
    lines: Sequence[Mapping[str, Any]], branch_index: int
) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    cursor = branch_index + 1
    while cursor < min(len(lines), branch_index + 180):
        group: list[dict[str, Any]] = []
        search = cursor
        for role in _ROLES:
            found: dict[str, Any] | None = None
            found_end: int | None = None
            stop = min(len(lines), search + 28, branch_index + 180)
            for index in range(search, stop):
                for width in range(1, min(_MAX_ROLE_ANCHOR_LINE_SPAN, stop - index) + 1):
                    surface = " ".join(
                        line["vietocr_text"].strip() for line in lines[index : index + width]
                    ).strip()
                    kind = match_vietnamese_anchor_alias_v1(surface, _ROLE_ALIASES[role])
                    if kind is None:
                        continue
                    found = {
                        "match_kind": kind,
                        "role": role,
                        "source_line_index": index,
                        "surface": surface,
                    }
                    found_end = index + width - 1
                    break
                if found is not None:
                    break
            if found is None:
                group = []
                break
            group.append(found)
            assert found_end is not None
            search = found_end + 1
        if not group:
            break
        groups.append(group)
        cursor = search
    return groups


def _header_anchor(
    lines: Sequence[Mapping[str, Any]],
    aliases: Sequence[str],
) -> dict[str, Any] | None:
    direct = [
        line
        for line in lines
        if match_vietnamese_anchor_alias_v1(line["vietocr_text"], aliases) is not None
    ]
    if direct:
        line = direct[-1]
        return {
            "source_line_indices": [line["source_line_index"]],
            "surface": line["vietocr_text"],
            "x_center_x2": center_x2_v1(line),
        }
    first = [
        line
        for line in lines
        if normalize_vietnamese_anchor_v1(line["vietocr_text"]) in {"cho vay", "tong"}
    ]
    second = [
        line
        for line in lines
        if normalize_vietnamese_anchor_v1(line["vietocr_text"]) in {"khach hang", "cong"}
    ]
    pairs: list[tuple[int, Mapping[str, Any], Mapping[str, Any]]] = []
    for left in first:
        for right in second:
            left_box = left["bbox"]
            right_box = right["bbox"]
            overlap = min(left_box[2], right_box[2]) - max(left_box[0], right_box[0])
            distance = abs(center_x2_v1(left) - center_x2_v1(right))
            if overlap > 0 or distance <= max(
                left_box[2] - left_box[0], right_box[2] - right_box[0]
            ):
                pairs.append((distance, left, right))
    if not pairs:
        return None
    _, left, right = min(pairs, key=lambda item: item[0])
    combined = f"{left['vietocr_text']} {right['vietocr_text']}"
    if match_vietnamese_anchor_alias_v1(combined, aliases) is None:
        return None
    return {
        "source_line_indices": sorted([left["source_line_index"], right["source_line_index"]]),
        "surface": combined,
        "x_center_x2": (center_x2_v1(left) + center_x2_v1(right)) // 2,
    }


def _sparse_money_vector(
    run: Sequence[Mapping[str, Any]],
    column_centers: Sequence[int],
    *,
    primary_numeric_authority: bool,
) -> list[dict[str, Any]] | None:
    """Bind present cells to geometric columns without inventing blank zeros."""

    if len(column_centers) < 2 or list(column_centers) != sorted(set(column_centers)):
        return None
    minimum_gap = min(
        right - left for left, right in zip(column_centers, column_centers[1:], strict=False)
    )
    maximum_distance = max(8, minimum_gap // 3)
    by_column: dict[int, dict[str, Any]] = {}
    for line in run:
        center = center_x2_v1(line)
        distances = [abs(center - expected) for expected in column_centers]
        column_index = min(range(len(distances)), key=distances.__getitem__)
        if distances[column_index] > maximum_distance or column_index in by_column:
            return None
        singleton = extract_typed_value_vector_v1(
            [line],
            ["MONEY"],
            primary_numeric_authority=primary_numeric_authority,
        )
        if singleton is None:
            return None
        item = singleton[0]
        item["lane_index"] = column_index
        by_column[column_index] = item
    return [by_column[index] for index in sorted(by_column)]


def _ordinary_graph(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    region: Mapping[str, Any],
) -> dict[str, Any]:
    lines = page["lines"]
    branch_index = region["branch_source_line_index"]
    role_indices = region["child_source_line_indices"]
    header = lines[branch_index + 1 : role_indices[0]]
    immediate_counts: list[int] = []
    for ordinal, role_index in enumerate(role_indices):
        stop = role_indices[ordinal + 1] if ordinal + 1 < len(role_indices) else len(lines)
        run, _ = _immediate_numeric_run(lines, role_index + 1, stop)
        immediate_counts.append(len(run))
    lane_count = min(immediate_counts) if immediate_counts else 0
    lane_types, unit_scope, reasons = _lane_axis(pages, page, header, lane_count, branch_index)
    reasons.extend(
        reason for reason in region["unresolved_reasons"] if reason != "OWNER_CONTEXT_NOT_RESOLVED"
    )
    if lane_count not in {2, 4}:
        reasons.append("ORDINARY_VALUE_LANE_COUNT_NOT_RESOLVED")
    axes, period_mode = extract_period_axis_v1(header)
    if len(axes) != 2:
        reasons.append("PERIOD_AXIS_NOT_RESOLVED")

    rows: list[dict[str, Any]] = []
    nonadditive_rows: list[dict[str, Any]] = []
    final_cursor = role_indices[-1] + 1
    for ordinal, (role, role_index, match_record) in enumerate(
        zip(_ROLES, role_indices, region["child_match_records"], strict=True)
    ):
        stop = role_indices[ordinal + 1] if ordinal + 1 < len(role_indices) else len(lines)
        run, cursor = _immediate_numeric_run(lines, role_index + 1, stop)
        if lane_count and len(run) > lane_count:
            cursor = run[lane_count - 1]["source_line_index"] + 1
            run = run[:lane_count]
        try:
            vector = (
                extract_typed_value_vector_v1(
                    run,
                    lane_types,
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                if lane_types
                else None
            )
        except AccountingTableAxesV1Error as error:
            raise _error(str(error)) from error
        if vector is None:
            reasons.append(f"{role}_VALUE_LANES_NOT_RESOLVED")
            vector = []
        rows.append(
            {
                "label": {
                    "match_kind": match_record["match_kind"],
                    "source_line_index": role_index,
                    "surface": match_record["surface"],
                },
                "role": role,
                "values": vector,
            }
        )
        if ordinal == len(_ROLES) - 1:
            final_cursor = cursor
            continue
        remainder = lines[cursor:stop]
        if not remainder:
            continue
        numeric_runs = _numeric_runs(remainder)
        label_surface = " ".join(
            line["vietocr_text"]
            for line in remainder
            if not is_number_like_v1(line["vietocr_text"])
        ).strip()
        normalized = normalize_vietnamese_anchor_v1(label_surface)
        if (
            "trong do" not in normalized
            or len(numeric_runs) != 1
            or len(numeric_runs[0]) != lane_count
        ):
            reasons.append(f"{role}_INTERMEDIATE_ROW_NOT_CLASSIFIED")
            continue
        vector = extract_typed_value_vector_v1(
            numeric_runs[0],
            lane_types,
            primary_numeric_authority=page["primary_numeric_authority"],
        )
        if vector is None:
            reasons.append(f"{role}_NONADDITIVE_VALUE_LANES_NOT_RESOLVED")
        nonadditive_rows.append(
            {
                "classification": "NONADDITIVE_INCLUDED_DISCLOSURE",
                "label_source_line_indices": [
                    line["source_line_index"]
                    for line in remainder
                    if not is_number_like_v1(line["vietocr_text"])
                ],
                "label_surface": label_surface,
                "parent_role": role,
                "values": vector or [],
            }
        )

    tail = lines[final_cursor : final_cursor + 32]
    boundary = next(
        (
            index
            for index, line in enumerate(tail)
            if (
                "phan tich" in normalize_vietnamese_anchor_v1(line["vietocr_text"])
                or _SECTION_NUMBER.fullmatch(line["vietocr_text"].strip()) is not None
            )
        ),
        None,
    )
    if boundary is not None:
        tail = tail[:boundary]
    first_label = next(
        (index for index, line in enumerate(tail) if not is_number_like_v1(line["vietocr_text"])),
        None,
    )
    core_total: list[dict[str, Any]] = []
    additive_row: dict[str, Any] | None = None
    grand_total: list[dict[str, Any]] = []
    if first_label is None:
        numeric, _ = _immediate_numeric_run(tail, 0, len(tail))
        if len(numeric) == lane_count:
            core_total = (
                extract_typed_value_vector_v1(
                    numeric,
                    lane_types,
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                or []
            )
        else:
            reasons.append("CORE_TOTAL_NOT_RESOLVED")
    else:
        before = [line for line in tail[:first_label] if is_number_like_v1(line["vietocr_text"])]
        if before:
            if len(before) != lane_count:
                reasons.append("CORE_TOTAL_NOT_RESOLVED")
            else:
                core_total = (
                    extract_typed_value_vector_v1(
                        before,
                        lane_types,
                        primary_numeric_authority=page["primary_numeric_authority"],
                    )
                    or []
                )
        label_end = first_label
        while label_end < len(tail) and not is_number_like_v1(tail[label_end]["vietocr_text"]):
            label_end += 1
        label_lines = tail[first_label:label_end]
        label_surface = " ".join(line["vietocr_text"] for line in label_lines)
        normalized = normalize_vietnamese_anchor_v1(label_surface)
        numeric = [line for line in tail[label_end:] if is_number_like_v1(line["vietocr_text"])]
        if "tong" in normalized:
            if before or len(numeric) != lane_count:
                reasons.append("LABELED_CORE_TOTAL_NOT_RESOLVED")
            else:
                core_total = (
                    extract_typed_value_vector_v1(
                        numeric,
                        lane_types,
                        primary_numeric_authority=page["primary_numeric_authority"],
                    )
                    or []
                )
        elif not any(token in normalized for token in ("margin", "ky quy", "ung truoc")):
            reasons.append("POST_GRADE_OPTIONAL_ROW_NOT_CLASSIFIED")
        elif len(numeric) != lane_count * 2:
            reasons.append("ADDITIVE_ROW_AND_GRAND_TOTAL_NOT_RESOLVED")
        else:
            additive_vector = (
                extract_typed_value_vector_v1(
                    numeric[:lane_count],
                    lane_types,
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                or []
            )
            grand_total = (
                extract_typed_value_vector_v1(
                    numeric[lane_count:],
                    lane_types,
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                or []
            )
            additive_row = {
                "classification": "ADDITIVE_MARGIN_OR_ADVANCE_CHILD",
                "label_source_line_indices": [line["source_line_index"] for line in label_lines],
                "label_surface": label_surface,
                "values": additive_vector,
            }

    numeric_authoritative = page["primary_numeric_authority"] and all(
        row["values"] and all(item["source_authoritative"] is True for item in row["values"])
        for row in rows
    )
    arithmetic = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    if numeric_authoritative:
        row_money = [money_values_v1(row["values"]) for row in rows]
        core_money = money_values_v1(core_total) if core_total else None
        grand_money = money_values_v1(grand_total) if grand_total else None
        additive_money = money_values_v1(additive_row["values"]) if additive_row else None
        if all(value is not None for value in row_money):
            typed = [value for value in row_money if value is not None]
            sums = [sum(value[index] for value in typed) for index in range(len(typed[0]))]
            if additive_row is None:
                money_ok = core_money == sums and not grand_total
            else:
                money_ok = (
                    additive_money is not None
                    and (not core_total or core_money == sums)
                    and grand_money
                    == [sums[index] + additive_money[index] for index in range(len(sums))]
                )
            percent_total_vector = grand_total if additive_row is not None else core_total
            percent_ok = True
            if "PERCENT" in lane_types:
                row_percent = [percentage_values_v1(row["values"]) for row in rows]
                total_percent = percentage_values_v1(percent_total_vector)
                additive_percent = (
                    percentage_values_v1(additive_row["values"])
                    if additive_row is not None
                    else None
                )
                if all(value is not None for value in row_percent):
                    typed_percent = [value for value in row_percent if value is not None]
                    percent_sums = [
                        sum(value[index] for value in typed_percent)
                        for index in range(len(typed_percent[0]))
                    ]
                    if additive_percent is not None:
                        percent_sums = [
                            percent_sums[index] + additive_percent[index]
                            for index in range(len(percent_sums))
                        ]
                    percent_ok = (
                        total_percent == percent_sums == [Decimal("100.00")] * len(percent_sums)
                    )
                else:
                    percent_ok = False
            arithmetic = (
                "CORROBORATED_GRADE_POPULATION"
                if money_ok and percent_ok
                else "VETOED_GRADE_POPULATION_MISMATCH"
            )
        else:
            arithmetic = "VETOED_GRADE_POPULATION_MISMATCH"
        if arithmetic.startswith("VETOED"):
            reasons.append("ARITHMETIC_POPULATION_VETO")

    if region["owner_context"] is None:
        reasons.append("CUSTOMER_LOAN_OWNER_NOT_RESOLVED")
    structural = not reasons
    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if structural and arithmetic == "CORROBORATED_GRADE_POPULATION"
        else (
            "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            if structural and arithmetic == "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            else "UNRESOLVED"
        )
    )
    return {
        "arithmetic_status": arithmetic,
        "axes": axes,
        "branch": {
            **canonical_clone_v1(region["branch_match"]),
            "source_line_index": branch_index,
        },
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "nonadditive_rows": nonadditive_rows,
        "optional_additive_row": additive_row,
        "owner_context": canonical_clone_v1(region["owner_context"]),
        "page_sequence": page["page_sequence"],
        "period_mode": period_mode,
        "rows": rows,
        "status": status,
        "totals": {"core": core_total, "grand": grand_total},
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }


def _stacked_graph(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    region: Mapping[str, Any],
) -> dict[str, Any]:
    lines = page["lines"]
    branch_index = region["branch_source_line_index"]
    groups = _role_groups(lines, branch_index)
    reasons: list[str] = [
        reason for reason in region["unresolved_reasons"] if reason != "OWNER_CONTEXT_NOT_RESOLVED"
    ]
    if region["owner_context"] is None:
        reasons.append("LOAN_QUALITY_OWNER_NOT_RESOLVED")
    if len(groups) != 2:
        reasons.append("EXACT_TWO_STACKED_PERIOD_BLOCKS_NOT_RESOLVED")
    usable = groups[:2]
    first_role = usable[0][0]["source_line_index"] if usable else len(lines)
    header = lines[branch_index + 1 : first_role]
    customer_header = _header_anchor(header, ["Cho vay khách hàng"])
    total_header = _header_anchor(header, ["Tổng cộng"])
    if customer_header is None:
        reasons.append("CUSTOMER_LOAN_TARGET_COLUMN_NOT_RESOLVED")
    if total_header is None:
        reasons.append("TOTAL_COMPANION_COLUMN_NOT_RESOLVED")
    axes, period_mode = extract_period_axis_v1(lines[branch_index + 1 :])
    if len(axes) != 2:
        reasons.append("STACKED_PERIOD_AXIS_NOT_RESOLVED")

    first_run: list[Mapping[str, Any]] = []
    if usable:
        first_run, _ = _immediate_numeric_run(
            lines,
            usable[0][0]["source_line_index"] + 1,
            usable[0][1]["source_line_index"],
        )
    column_count = len(first_run)
    if column_count < 3:
        reasons.append("MULTI_ASSET_COLUMN_AXIS_NOT_RESOLVED")
    column_centers = sorted(center_x2_v1(line) for line in first_run)

    target_column_index: int | None = None
    total_column_index: int | None = None
    if column_count and first_run and customer_header is not None:
        distances = [abs(center - customer_header["x_center_x2"]) for center in column_centers]
        target_column_index = min(range(len(distances)), key=distances.__getitem__)
        if distances.count(distances[target_column_index]) != 1:
            target_column_index = None
            reasons.append("CUSTOMER_LOAN_TARGET_COLUMN_GEOMETRY_AMBIGUOUS")
        if total_header is not None:
            total_distances = [
                abs(center - total_header["x_center_x2"]) for center in column_centers
            ]
            total_column_index = min(range(len(total_distances)), key=total_distances.__getitem__)
            if total_distances.count(total_distances[total_column_index]) != 1:
                total_column_index = None
                reasons.append("TOTAL_COLUMN_GEOMETRY_AMBIGUOUS")
    unit_lines = [
        line for line in lines[:first_role] if unit_kind_v1(line["vietocr_text"]) == "MONEY"
    ]
    inherited = _inherited_document_unit(pages, page["page_sequence"], branch_index)
    if not unit_lines and inherited is None:
        reasons.append("UNIT_SCOPE_NOT_RESOLVED")
        unit_scope: dict[str, Any] = {"mode": "UNRESOLVED"}
    elif unit_lines:
        unit_scope = {
            "mode": "LOCAL_SHARED_MONEY_UNIT",
            "source_line_indices": [line["source_line_index"] for line in unit_lines],
        }
    else:
        unit_scope = {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}

    blocks: list[dict[str, Any]] = []
    for group_offset, group in enumerate(usable):
        next_group_start = (
            usable[group_offset + 1][0]["source_line_index"]
            if group_offset + 1 < len(usable)
            else len(lines)
        )
        rows: list[dict[str, Any]] = []
        final_cursor = group[-1]["source_line_index"] + 1
        for role_offset, match in enumerate(group):
            stop = (
                group[role_offset + 1]["source_line_index"]
                if role_offset + 1 < len(group)
                else next_group_start
            )
            run, cursor = _immediate_numeric_run(lines, match["source_line_index"] + 1, stop)
            if column_count and len(run) > column_count:
                cursor = run[column_count - 1]["source_line_index"] + 1
                run = run[:column_count]
            vector = (
                _sparse_money_vector(
                    run,
                    column_centers,
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                if column_count
                else None
            )
            present_columns = (
                {item["lane_index"] for item in vector} if vector is not None else set()
            )
            if (
                vector is None
                or target_column_index is None
                or total_column_index is None
                or not {target_column_index, total_column_index}.issubset(present_columns)
            ):
                reasons.append(f"STACKED_BLOCK_{group_offset}_{match['role']}_VALUES_UNRESOLVED")
                vector = []
            rows.append({"label": match, "role": match["role"], "values": vector})
            if role_offset == len(group) - 1:
                final_cursor = cursor
        total_runs = [
            run
            for run in _numeric_runs(lines[final_cursor:next_group_start])
            if len(run) == column_count
        ]
        total = (
            extract_typed_value_vector_v1(
                total_runs[0],
                ["MONEY"] * column_count,
                primary_numeric_authority=page["primary_numeric_authority"],
            )
            if total_runs
            else None
        )
        if total is None:
            reasons.append(f"STACKED_BLOCK_{group_offset}_TOTAL_UNRESOLVED")
            total = []
        blocks.append({"block_ordinal": group_offset, "rows": rows, "total": total})

    arithmetic = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    if page["primary_numeric_authority"] and blocks:
        block_checks: list[bool] = []
        for block in blocks:
            if any(
                [item["lane_index"] for item in row["values"]] != list(range(column_count))
                for row in block["rows"]
            ):
                block_checks.append(False)
                continue
            row_vectors = [money_values_v1(row["values"]) for row in block["rows"]]
            total_vector = money_values_v1(block["total"])
            if any(value is None for value in row_vectors) or total_vector is None:
                block_checks.append(False)
                continue
            typed = [value for value in row_vectors if value is not None]
            column_ok = [
                sum(value[index] for value in typed) for index in range(column_count)
            ] == total_vector
            row_ok = total_column_index is not None and all(
                sum(value[index] for index in range(column_count) if index != total_column_index)
                == value[total_column_index]
                for value in typed
            )
            block_checks.append(column_ok and row_ok)
        arithmetic = (
            "CORROBORATED_STACKED_ROW_AND_COLUMN_POPULATIONS"
            if len(block_checks) == 2 and all(block_checks)
            else "VETOED_STACKED_POPULATION_MISMATCH"
        )
        if arithmetic.startswith("VETOED"):
            reasons.append("ARITHMETIC_POPULATION_VETO")

    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if not reasons and arithmetic == "CORROBORATED_STACKED_ROW_AND_COLUMN_POPULATIONS"
        else (
            "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            if not reasons and arithmetic == "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            else "UNRESOLVED"
        )
    )
    return {
        "arithmetic_status": arithmetic,
        "axes": axes,
        "blocks": blocks,
        "branch": {
            **canonical_clone_v1(region["branch_match"]),
            "source_line_index": branch_index,
        },
        "customer_loan_column": {
            "column_index": target_column_index,
            "header": customer_header,
        },
        "layout_mode": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
        "owner_context": canonical_clone_v1(region["owner_context"]),
        "page_sequence": page["page_sequence"],
        "period_mode": period_mode,
        "status": status,
        "total_column": {"column_index": total_column_index, "header": total_header},
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }


def _graph(pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]) -> dict[str, Any]:
    page = _page_by_sequence(pages, region["page_sequence"])
    lines = page["lines"]
    if len(_role_groups(lines, region["branch_source_line_index"])) >= 2:
        return _stacked_graph(pages, page, region)
    return _ordinary_graph(pages, page, region)


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-quality document graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["status"]
        not in {
            "ACCEPTED_UNIQUE_VARIANT_GRAPH",
            "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED",
            "UNRESOLVED_NO_COMPLETE_REGION",
        }
        or type(value["graphs"]) is not list
        or not same_typed_json_v1(value["safety"], _SAFETY)
    ):
        raise _error("loan-quality document graph identity/safety drifted")
    metrics = value["metrics"]
    expected_metrics = {
        "accepted_graph_count": sum(
            graph["status"] == "ACCEPTED_VARIANT_GRAPH" for graph in value["graphs"]
        ),
        "complete_anchor_region_count": len(value["graphs"]),
        "near_region_count": len(value["region_scan"]["near_regions"]),
        "numeric_unresolved_graph_count": sum(
            graph["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED" for graph in value["graphs"]
        ),
        "structurally_resolved_graph_count": sum(
            graph["status"] in {"ACCEPTED_VARIANT_GRAPH", "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"}
            for graph in value["graphs"]
        ),
        "unresolved_graph_count": sum(graph["status"] == "UNRESOLVED" for graph in value["graphs"]),
    }
    if not same_typed_json_v1(metrics, expected_metrics):
        raise _error("loan-quality document graph metrics drifted")
    accepted = metrics["structurally_resolved_graph_count"]
    expected_uniqueness = {
        "full_match_count": accepted,
        "status": (
            "UNIQUE_FULL_MATCH"
            if accepted == 1
            else "MULTIPLE_FULL_MATCHES"
            if accepted > 1
            else "NO_FULL_MATCH"
        ),
    }
    if not same_typed_json_v1(value["uniqueness"], expected_uniqueness):
        raise _error("loan-quality document uniqueness evidence drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lqvgv1:document:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality document graph identity drifted")
    return canonical_clone_v1(value)


def build_loan_quality_variant_graph_document_v1(
    document_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Scan one entire PDF and build every loan-quality graph candidate."""

    pages = _pages(document_pages)
    region_scan = _engine_scan(pages)
    graphs = [_graph(pages, region) for region in region_scan["regions"]]
    metrics = {
        "accepted_graph_count": sum(
            graph["status"] == "ACCEPTED_VARIANT_GRAPH" for graph in graphs
        ),
        "complete_anchor_region_count": len(graphs),
        "near_region_count": len(region_scan["near_regions"]),
        "numeric_unresolved_graph_count": sum(
            graph["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED" for graph in graphs
        ),
        "structurally_resolved_graph_count": sum(
            graph["status"] in {"ACCEPTED_VARIANT_GRAPH", "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"}
            for graph in graphs
        ),
        "unresolved_graph_count": sum(graph["status"] == "UNRESOLVED" for graph in graphs),
    }
    uniqueness = {
        "full_match_count": metrics["structurally_resolved_graph_count"],
        "status": (
            "UNIQUE_FULL_MATCH"
            if metrics["structurally_resolved_graph_count"] == 1
            else (
                "MULTIPLE_FULL_MATCHES"
                if metrics["structurally_resolved_graph_count"] > 1
                else "NO_FULL_MATCH"
            )
        ),
    }
    status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if uniqueness["status"] == "UNIQUE_FULL_MATCH" and metrics["accepted_graph_count"] == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if not graphs
            else "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
        )
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": metrics,
        "region_scan": region_scan,
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "uniqueness": uniqueness,
    }
    return _validate_result(
        {
            **material,
            "result_id": "lqvgv1:document:" + canonical_json_sha256_v1(material),
        }
    )


def validate_loan_quality_variant_graph_replay_v1(
    value: Any,
    document_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rebuild from the complete PDF line axis and exact-compare."""

    persisted = _validate_result(value)
    rebuilt = build_loan_quality_variant_graph_document_v1(document_pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-quality document graph does not replay exactly")
    return rebuilt
