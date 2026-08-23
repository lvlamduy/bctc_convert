"""Bank-blind V2 graph for five-grade customer-loan quality tables.

V2 keeps the V1 artifact and replay contract untouched.  It delegates label
topology, adaptive row/column geometry, period parsing, and typed value
extraction to shared accounting primitives.  The family layer below only
declares the five grades, identifies customer-loan context, separates the
ordinary/stacked presentations, and evaluates the family equations.

Provider line order is never table order.  Labels and repeated period blocks
are ordered by their immutable bounding boxes.  A numeric cell is one source
line candidate when either its bound source reader or fresh VietOCR exposes a
visible numeric surface; the two readers never manufacture duplicate cells.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from statistics import median
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    SPEC_FORMAT_VERSION,
    AccountingFamilyTopologyV1Error,
    build_accounting_family_topology_scan_v1,
    enumerate_accounting_family_role_occurrences_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    center_x2_v1,
    extract_period_axis_v1,
    extract_period_observations_v1,
    extract_row_aligned_typed_value_vector_v1,
    extract_typed_value_vector_v1,
    line_has_accounting_value_surface_v1,
    money_integer_v1,
    money_values_v1,
    percentage_values_v1,
    unit_kind_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    assign_value_row_lanes_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    median_text_height_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FAMILY_ID",
    "LOAN_QUALITY_TOPOLOGY_SPEC_V2",
    "LoanQualityVariantGraphV2Error",
    "build_loan_quality_variant_graph_document_v2",
    "validate_loan_quality_variant_graph_document_v2",
    "validate_loan_quality_variant_graph_replay_v2",
]


FORMAT_VERSION = "LOAN_QUALITY_VARIANT_GRAPH_DOCUMENT_V2"
FAMILY_ID = "LOAN_QUALITY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_DOCUMENT_FRESH_VIETOCR_AND_BOUND_SOURCE_NUMERIC_"
    "VISUAL_ROLE_ROW_STACKED_BLOCK_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_GRAPH_"
    "PROPOSAL_ONLY_NO_SCHEMA_MAPPING_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")
_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "STANDARD": ("Nợ đủ tiêu chuẩn", "Nhóm 1 Nợ đủ tiêu chuẩn", "Nợ nhóm 1"),
    "SPECIAL_MENTION": ("Nợ cần chú ý", "Nhóm 2 Nợ cần chú ý", "Nợ nhóm 2"),
    "SUBSTANDARD": (
        "Nợ dưới tiêu chuẩn",
        "Nhóm 3 Nợ dưới tiêu chuẩn",
        "Nợ nhóm 3",
    ),
    "DOUBTFUL": ("Nợ nghi ngờ", "Nhóm 4 Nợ nghi ngờ", "Nợ nhóm 4"),
    "LOSS": (
        "Nợ có khả năng mất vốn",
        "Nhóm 5 Nợ có khả năng mất vốn",
        "Nợ nhóm 5",
    ),
}
_BRANCH_ALIASES = (
    "Phân tích chất lượng nợ cho vay",
    "Phân tích chất lượng dư nợ cho vay khách hàng",
    "Phân tích chất lượng dư nợ cho vay",
    "Phân tích dư nợ cho vay theo chất lượng nợ",
    "Phân tích dư nợ theo chất lượng nợ cho vay",
    "Phân tích dư nợ theo chất lượng nợ",
    "Theo chất lượng nợ cho vay",
    "Theo chất lượng dư nợ cho vay",
    "Phân loại chất lượng tài sản có rủi ro tín dụng",
    "Chi tiết phân loại chất lượng tài sản có rủi ro tín dụng tại Ngân hàng như sau",
)
_OWNER_ALIASES = (
    "Cho vay khách hàng",
    "Các khoản cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
    "Rủi ro tín dụng",
)
_RESET_ALIASES = (
    "Phân tích dư nợ theo thời gian",
    "Phân tích dư nợ theo thời gian gốc của khoản vay",
    "Phân tích dư nợ cho vay theo thời gian",
    "Phân tích dư nợ cho vay theo thời gian gốc của khoản vay",
    "Phân tích dư nợ cho vay theo thời hạn gốc của khoản vay",
    "Phân tích dư nợ theo ngành",
    "Phân tích dư nợ cho vay theo ngành",
    "Phân tích dư nợ theo ngành nghề kinh tế",
    "Phân tích dư nợ cho vay theo ngành nghề kinh tế",
    "Phân tích dư nợ theo đối tượng khách hàng",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "Dự phòng rủi ro cho vay khách hàng",
    "Nghiệp vụ phát hành thư tín dụng trả chậm",
    "Nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản trả ngay",
    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
)
_HARD_NEGATIVE_ALIASES = (
    "Phân tích chất lượng tiền gửi và cho vay các TCTD khác",
    "Phân tích chất lượng dư nợ tiền gửi và cho vay các TCTD khác",
    "Phân tích chất lượng hoạt động mua nợ",
)

LOAN_QUALITY_TOPOLOGY_SPEC_V2 = {
    "children": [
        {
            "aliases": list(_ROLE_ALIASES[role]),
            "presence": "REQUIRED",
            "role": role,
            "role_kind": "ADDITIVE_CHILD",
        }
        for role in _ROLES
    ],
    "family_id": FAMILY_ID,
    "format_version": SPEC_FORMAT_VERSION,
    "hard_negative_aliases": list(_HARD_NEGATIVE_ALIASES),
    "limits": {
        "max_cluster_span_lines": 240,
        "max_continuation_pages": 0,
        "max_label_line_span": 3,
    },
    "parent": {
        "aliases": list(_BRANCH_ALIASES),
        "resolution_mode": "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER",
        "role": "LOAN_QUALITY_BRANCH",
    },
    "structural_reset_aliases": list(_RESET_ALIASES),
}

_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "blank_companion_cells_imputed_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "exact_duplicate_candidates_collapsed_only_by_bound_evidence": True,
    "fresh_vietocr_transformer_text_required": True,
    "legacy_ocr_used_for_semantic_anchors": False,
    "mapping_authority": False,
    "nonadditive_or_excluded_rows_silently_added": False,
    "numeric_authority_requires_bound_source_surface": True,
    "percentage_or_companion_columns_silently_discarded": False,
    "persisted_result_self_authenticating": False,
    "provider_line_order_used_as_visual_row_order": False,
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
_SECTION_NUMBER = re.compile(r"^\d{1,3}(?:\.\d{1,3}){1,2}\.?$", re.ASCII)
_SECTION_HEADING_PREFIX = re.compile(r"^\d{1,3}(?:\.\d{1,3}){1,2}\.?\s+", re.ASCII)
_MONEY_BEFORE_UNIT = re.compile(
    r"(?P<value>\(?[-+]?\d(?:[\d.,]|[ \u00a0](?=\d))*\)?)"
    r"\s*(?:triệu|trieu)\s*(?:đồng|dong)",
    re.IGNORECASE,
)


class LoanQualityVariantGraphV2Error(ValueError):
    """The complete-document line axis, V2 graph, or replay drifted."""


def _error(message: str) -> LoanQualityVariantGraphV2Error:
    return LoanQualityVariantGraphV2Error(message)


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
        raise _error("loan-quality V2 scan requires one non-empty complete PDF page sequence")
    pages: list[dict[str, Any]] = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error(f"loan-quality V2 page {page_offset} fields drifted")
        if (
            type(raw_page["page_sequence"]) is not int
            or raw_page["page_sequence"] != page_offset + 1
            or type(raw_page["primary_numeric_authority"]) is not bool
            or type(raw_page["lines"]) is not list
        ):
            raise _error("loan-quality V2 page sequence, authority, or line axis drifted")
        lines: list[dict[str, Any]] = []
        for line_offset, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-quality V2 semantic line fields drifted")
            if (
                type(raw_line["source_line_index"]) is not int
                or raw_line["source_line_index"] != line_offset
                or type(raw_line["vietocr_text"]) is not str
                or (
                    raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str
                )
            ):
                raise _error("loan-quality V2 semantic line identity/text drifted")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], "loan-quality V2 semantic line"),
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
    return pages


def _topology_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["source_line_index"],
                    "source_text": line["source_text"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _page(pages: Sequence[Mapping[str, Any]], page_sequence: int) -> Mapping[str, Any]:
    return pages[page_sequence - 1]


def _line_is_numeric(line: Mapping[str, Any]) -> bool:
    return line_has_accounting_value_surface_v1(line)


def _line_indices(match: Mapping[str, Any]) -> list[int]:
    explicit = match.get("source_line_indices")
    if explicit is not None:
        return list(explicit)
    return list(range(match["source_line_index"], match["end_source_line_index"] + 1))


def _union_bbox(lines: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> list[int]:
    boxes = [lines[index]["bbox"] for index in indices]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _public_label(lines: Sequence[Mapping[str, Any]], match: Mapping[str, Any]) -> dict[str, Any]:
    indices = _line_indices(match)
    return {
        "bbox": _union_bbox(lines, indices),
        "match_kind": match["match_kind"],
        "source_line_indices": indices,
        "surface": match["surface"],
    }


def _visual_labels(
    page: Mapping[str, Any], occurrences: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    lines = page["lines"]
    labels = [
        {
            "label": _public_label(lines, match),
            "role": match["role"],
        }
        for match in occurrences
        if match["page_sequence"] == page["page_sequence"]
    ]
    labels.sort(
        key=lambda item: (
            item["label"]["bbox"][1] + item["label"]["bbox"][3],
            item["label"]["bbox"][0],
            item["label"]["source_line_indices"],
        )
    )
    deduplicated: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}
    for item in labels:
        key = (item["role"], tuple(item["label"]["source_line_indices"]))
        deduplicated.setdefault(key, item)
    return sorted(
        deduplicated.values(),
        key=lambda item: (
            item["label"]["bbox"][1] + item["label"]["bbox"][3],
            item["label"]["bbox"][0],
            item["label"]["source_line_indices"],
        ),
    )


def _branch_surface_kind(normalized: str) -> str | None:
    if "tctd" in normalized and "tai san co rui ro tin dung" not in normalized:
        return None
    patterns = (
        "phan tich chat luong no cho vay",
        "phan tich chat luong du no cho vay",
        "phan tich du no cho vay theo chat luong no",
        "phan tich du no theo chat luong no",
        "theo chat luong no cho vay",
        "theo chat luong du no cho vay",
        "phan loai chat luong tai san co rui ro tin dung",
    )
    return next((pattern for pattern in patterns if pattern in normalized), None)


def _branch_candidates(page: Mapping[str, Any], *, first_role_top: int) -> list[dict[str, Any]]:
    candidates = []
    for line in page["lines"]:
        if line["bbox"][1] >= first_role_top:
            continue
        normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
        variant = _branch_surface_kind(normalized)
        if variant is None:
            continue
        candidates.append(
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "match_kind": "ACCENTLESS_BRANCH_PHRASE_IN_COMPLETE_FAMILY_TOPOLOGY",
                "normalized_surface": normalized,
                "source_line_indices": [line["source_line_index"]],
                "surface": line["vietocr_text"],
                "variant": variant,
            }
        )
    return sorted(candidates, key=lambda item: (item["bbox"][1], item["source_line_indices"]))


def _owner_surface(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value)
    normalized = re.sub(r"^(?:\d+\s+)+", "", normalized)
    normalized = re.sub(r"\s+tiep theo$", "", normalized)
    return normalized


def _within_one_edit(value: str, expected: str) -> bool:
    if value == expected:
        return True
    if abs(len(value) - len(expected)) > 1:
        return False
    if len(value) == len(expected):
        return sum(left != right for left, right in zip(value, expected, strict=True)) <= 1
    shorter, longer = (value, expected) if len(value) < len(expected) else (expected, value)
    for offset in range(len(longer)):
        if longer[:offset] + longer[offset + 1 :] == shorter:
            return True
    return False


def _owner_match_kind(surface: str) -> tuple[str, str] | None:
    aliases = {normalize_vietnamese_anchor_v1(alias) for alias in _OWNER_ALIASES}
    normalized = _owner_surface(surface)
    if normalized in aliases:
        return "EXACT_ACCENTLESS_ALIAS", normalized
    raw = normalize_vietnamese_anchor_v1(surface)
    for alias in aliases:
        if not raw.startswith(alias + " "):
            continue
        suffix = raw[len(alias) + 1 :].split()
        if len(suffix) == 2 and suffix[1] == "theo" and _within_one_edit(suffix[0], "tiep"):
            return "BOUNDED_ONE_EDIT_CONTINUATION_SUFFIX", alias
    return None


def _owner_hits(page: Mapping[str, Any], before_top: int) -> list[dict[str, Any]]:
    lines = page["lines"]
    hits = []
    for start in range(len(lines)):
        selected: dict[str, Any] | None = None
        for width in range(1, min(3, len(lines) - start) + 1):
            subset = lines[start : start + width]
            if min(line["bbox"][1] for line in subset) >= before_top:
                continue
            surface = " ".join(line["vietocr_text"].strip() for line in subset).strip()
            matched = _owner_match_kind(surface)
            if matched is None:
                continue
            match_kind, normalized = matched
            box = _union_bbox(lines, list(range(start, start + width)))
            selected = {
                "bbox": box,
                "match_kind": match_kind,
                "mode": "SAME_PAGE_PRECEDING_CONTEXT",
                "normalized_surface": normalized,
                "page_sequence": page["page_sequence"],
                "source_line_indices": list(range(start, start + width)),
                "surface": surface,
            }
            break
        if selected is not None:
            hits.append(selected)
    return hits


def _owner_context(
    pages: Sequence[Mapping[str, Any]], page: Mapping[str, Any], first_role_top: int
) -> dict[str, Any] | None:
    same_page = _owner_hits(page, first_role_top)
    if same_page:
        return canonical_clone_v1(
            max(same_page, key=lambda item: (item["bbox"][1], item["source_line_indices"]))
        )
    if page["page_sequence"] == 1:
        return None
    previous = pages[page["page_sequence"] - 2]
    hits = _owner_hits(previous, 10**12)
    if not hits:
        return None
    selected = canonical_clone_v1(
        max(hits, key=lambda item: (item["bbox"][1], item["source_line_indices"]))
    )
    selected["mode"] = "IMMEDIATE_PREVIOUS_PAGE"
    return selected


def _is_boundary(line: Mapping[str, Any], *, page_width: int) -> bool:
    normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
    unnumbered = _SECTION_HEADING_PREFIX.sub("", normalized)
    if "nghiep vu phat hanh thu tin dung tra cham" in normalized:
        return True
    if normalized.startswith("du phong rui ro cho vay khach hang"):
        return True
    if unnumbered.startswith("phan tich") and not (
        "chat luong no cho vay" in unnumbered
        or "chat luong du no cho vay" in unnumbered
        or "tai san co rui ro tin dung" in unnumbered
    ):
        return True
    return (
        line["bbox"][2] < page_width * 0.4
        and _SECTION_NUMBER.fullmatch(line["vietocr_text"].strip()) is not None
    )


def _table_bottom_y(
    page: Mapping[str, Any], labels: Sequence[Mapping[str, Any]], *, first_role_top: int
) -> int:
    page_width = max((line["bbox"][2] for line in page["lines"]), default=1)
    loss_bottoms = [item["label"]["bbox"][3] for item in labels if item["role"] == "LOSS"]
    search_top = min(loss_bottoms) if loss_bottoms else first_role_top
    boundaries = [
        line["bbox"][1]
        for line in page["lines"]
        if line["bbox"][3] >= search_top and _is_boundary(line, page_width=page_width)
    ]
    return (
        min(boundaries)
        if boundaries
        else max((line["bbox"][3] for line in page["lines"]), default=first_role_top + 1) + 1
    )


def _role_groups(labels: Sequence[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    cursor = 0
    while cursor + len(_ROLES) <= len(labels):
        window = list(labels[cursor : cursor + len(_ROLES)])
        if tuple(item["role"] for item in window) != _ROLES:
            cursor += 1
            continue
        centers = [item["label"]["bbox"][1] + item["label"]["bbox"][3] for item in window]
        if centers != sorted(set(centers)):
            cursor += 1
            continue
        groups.append(window)
        cursor += len(_ROLES)
    return groups


def _page_width(page: Mapping[str, Any]) -> int:
    return max((line["bbox"][2] for line in page["lines"]), default=0) + 1


def _numeric_minimum_ratio(
    page: Mapping[str, Any], groups: Sequence[Sequence[Mapping[str, Any]]]
) -> float:
    width = _page_width(page)
    labels = [item["label"]["bbox"] for group in groups for item in group]
    right = float(median(box[2] for box in labels))
    height = float(median(box[3] - box[1] for box in labels))
    return max(0.05, min(0.45, (right + height * 0.5) / width))


def _table_lines_by_y(page: Mapping[str, Any], *, top: int, bottom: int) -> list[dict[str, Any]]:
    return [line for line in page["lines"] if line["bbox"][3] >= top and line["bbox"][1] < bottom]


def _column_centers(
    page: Mapping[str, Any], groups: Sequence[Sequence[Mapping[str, Any]]], bottom: int
) -> tuple[list[float], float]:
    top = min(item["label"]["bbox"][1] for group in groups for item in group)
    body = _table_lines_by_y(page, top=top, bottom=bottom)
    minimum_ratio = _numeric_minimum_ratio(page, groups)
    centers = infer_numeric_column_centers_v1(
        body,
        is_numeric=_line_is_numeric,
        page_width=_page_width(page),
        minimum_x_ratio=minimum_ratio,
        maximum_x_ratio=0.995,
    )
    return centers, minimum_ratio


def _period_line(line: Mapping[str, Any], page: Mapping[str, Any]) -> dict[str, Any]:
    challenger = line.get("source_text")
    return {
        **line,
        **(
            {"numeric_score": 1.0, "numeric_text": challenger}
            if page["primary_numeric_authority"] and type(challenger) is str
            else {}
        ),
    }


def _header_lines(
    page: Mapping[str, Any], branch: Mapping[str, Any] | None, first_label: Mapping[str, Any]
) -> list[dict[str, Any]]:
    top = branch["bbox"][1] if branch is not None else max(0, first_label["bbox"][1] - 500)
    first_top = first_label["bbox"][1]
    bottom = first_top + int(round(median_text_height_v1(page["lines"]) * 0.45))
    return [
        _period_line(line, page)
        for line in page["lines"]
        if line["bbox"][1] >= top and line["bbox"][1] < first_top and line["bbox"][3] <= bottom
    ]


def _inherited_unit(
    pages: Sequence[Mapping[str, Any]], page_sequence: int, before_top: int
) -> dict[str, Any] | None:
    candidates = []
    for page in pages[:page_sequence]:
        for line in page["lines"]:
            if page["page_sequence"] == page_sequence and line["bbox"][1] >= before_top:
                continue
            normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
            if unit_kind_v1(line["vietocr_text"]) == "MONEY" and (
                "don vi" in normalized
                or normalized in {"dong", "nghin dong", "trieu dong", "trieu vnd", "ty dong"}
            ):
                candidates.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["source_line_index"],
                        "surface": line["vietocr_text"],
                    }
                )
    return candidates[-1] if candidates else None


def _horizontal_axes(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    header: Sequence[Mapping[str, Any]],
    centers: Sequence[float],
    first_label_top: int,
) -> tuple[list[dict[str, Any]], str, list[str], dict[str, Any], list[str]]:
    reasons: list[str] = []
    try:
        periods, period_mode = extract_period_axis_v1(header)
    except AccountingTableAxesV1Error:
        periods, period_mode = [], "UNRESOLVED"
    if len(periods) != 2:
        reasons.append("TWO_PERIOD_AXIS_NOT_RESOLVED")
    local_units = [
        {
            "kind": kind,
            "source_line_index": line["source_line_index"],
            "surface": line["vietocr_text"],
            "x_center_x2": center_x2_v1(line),
        }
        for line in header
        if (kind := unit_kind_v1(line["vietocr_text"])) is not None
    ]
    local_units.sort(key=lambda item: item["x_center_x2"])
    if len(centers) == 4 and [item["kind"] for item in local_units] == [
        "MONEY",
        "PERCENT",
        "MONEY",
        "PERCENT",
    ]:
        lane_types = [item["kind"] for item in local_units]
        unit_scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [item["source_line_index"] for item in local_units],
            "surfaces": [item["surface"] for item in local_units],
        }
    elif (
        len(centers) == 2
        and len(local_units) == 2
        and all(item["kind"] == "MONEY" for item in local_units)
    ):
        lane_types = ["MONEY", "MONEY"]
        unit_scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [item["source_line_index"] for item in local_units],
            "surfaces": [item["surface"] for item in local_units],
        }
    elif len(centers) == 2 and len(local_units) == 1 and local_units[0]["kind"] == "MONEY":
        lane_types = ["MONEY", "MONEY"]
        unit_scope = {
            "mode": "LOCAL_SHARED_MONEY_UNIT",
            "source_line_indices": [local_units[0]["source_line_index"]],
            "surfaces": [local_units[0]["surface"]],
        }
    elif len(centers) == 2 and not local_units:
        inherited = _inherited_unit(pages, page["page_sequence"], first_label_top)
        lane_types = ["MONEY", "MONEY"]
        if inherited is None:
            unit_scope = {"mode": "UNRESOLVED"}
            reasons.append("UNIT_SCOPE_NOT_RESOLVED")
        else:
            unit_scope = {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}
    else:
        lane_types = []
        unit_scope = {"mode": "UNRESOLVED_LOCAL_UNIT_LAYOUT"}
        reasons.append("SUPPORTED_TYPED_LANE_AXIS_NOT_RESOLVED")
    return periods, period_mode, lane_types, unit_scope, reasons


def _centers_supported_by_visible_units(
    header: Sequence[Mapping[str, Any]], centers: Sequence[float]
) -> list[float]:
    unit_centers = sorted(
        center_x2_v1(line) / 2 for line in header if unit_kind_v1(line["vietocr_text"]) is not None
    )
    if len(unit_centers) not in {2, 4} or len(centers) <= len(unit_centers):
        return list(centers)
    selected = [
        min(range(len(centers)), key=lambda index: abs(centers[index] - unit_center))
        for unit_center in unit_centers
    ]
    if len(set(selected)) != len(unit_centers):
        return list(centers)
    return [centers[index] for index in sorted(selected)]


def _row_vector(
    page: Mapping[str, Any],
    label: Mapping[str, Any],
    lane_types: Sequence[str],
    centers: Sequence[float],
    table_lines: Sequence[Mapping[str, Any]],
    excluded_source_line_indices: set[int] | None = None,
) -> list[dict[str, Any]] | None:
    center_x2 = [int(round(center * 2)) for center in centers]
    if len(center_x2) < 2:
        return None
    lane_gap_x2 = min(right - left for left, right in zip(center_x2, center_x2[1:], strict=False))
    outer_tolerance_x2 = max(8, lane_gap_x2 * 2 // 5)
    aligned_lines = [
        line
        for line in table_lines
        if line["source_line_index"] not in (excluded_source_line_indices or set())
        if not _line_is_numeric(line)
        or center_x2[0] - outer_tolerance_x2
        <= center_x2_v1(line)
        <= center_x2[-1] + outer_tolerance_x2
    ]
    boxes = [page["lines"][index]["bbox"] for index in label["source_line_indices"]]
    raw_candidates = [label["bbox"], *reversed(boxes)]
    candidates = []
    for box in raw_candidates:
        inset = max(1, (box[3] - box[1]) // 3)
        if box[1] + inset < box[3] - inset:
            candidates.append([box[0], box[1] + inset, box[2], box[3] - inset])
        candidates.append(box)

    # Bind one complete visual baseline as a unit before considering the
    # lane-wise helper.  Adjacent rows can have overlapping detector boxes;
    # choosing each lane independently may otherwise splice two different
    # baselines into one synthetic row.  Consumed baselines are excluded by
    # the caller, so one observed cell cluster cannot populate two roles.
    clustered = cluster_numeric_rows_v1(
        aligned_lines,
        is_numeric=_line_is_numeric,
        start_index=-1,
        stop_index=max(
            (line["source_line_index"] for line in aligned_lines),
            default=0,
        )
        + 1,
        page_width=_page_width(page),
        minimum_x_ratio=0.0,
        maximum_x_ratio=1.0,
    )
    baseline_candidates: dict[tuple[int, ...], tuple[float, list[dict[str, Any]]]] = {}
    for cluster_lines in clustered:
        cluster = {
            "bottom": max(line["bbox"][3] for line in cluster_lines),
            "lines": list(cluster_lines),
            "top": min(line["bbox"][1] for line in cluster_lines),
        }
        vector = _cluster_vector(cluster, lane_types, centers, page)
        if vector is None:
            continue
        cluster_center_y_x2 = float(
            median(line["bbox"][1] + line["bbox"][3] for line in cluster_lines)
        )
        cluster_height = cluster["bottom"] - cluster["top"]
        scores = []
        for box in candidates:
            label_center_y_x2 = box[1] + box[3]
            label_height = box[3] - box[1]
            overlap = min(box[3], cluster["bottom"]) - max(box[1], cluster["top"])
            distance = abs(cluster_center_y_x2 - label_center_y_x2)
            if overlap > 0 or distance <= max(label_height, cluster_height):
                scores.append(distance)
        if not scores:
            continue
        signature = tuple(item["source_line_index"] for item in vector)
        score = min(scores)
        current = baseline_candidates.get(signature)
        if current is None or score < current[0]:
            baseline_candidates[signature] = (score, vector)
    if baseline_candidates:
        minimum = min(item[0] for item in baseline_candidates.values())
        best = [item[1] for item in baseline_candidates.values() if item[0] == minimum]
        return best[0] if len(best) == 1 else None

    resolved: dict[tuple[int, ...], tuple[float, list[dict[str, Any]]]] = {}
    for box in candidates:
        vector = extract_row_aligned_typed_value_vector_v1(
            aligned_lines,
            box,
            lane_types,
            center_x2,
            primary_numeric_authority=page["primary_numeric_authority"],
        )
        if vector is not None:
            signature = tuple(item["source_line_index"] for item in vector)
            label_center_y_x2 = box[1] + box[3]
            value_center_y_x2 = sum(
                page["lines"][item["source_line_index"]]["bbox"][1]
                + page["lines"][item["source_line_index"]]["bbox"][3]
                for item in vector
            ) / len(vector)
            score = abs(value_center_y_x2 - label_center_y_x2)
            current = resolved.get(signature)
            if current is None or score < current[0]:
                resolved[signature] = (score, vector)
    if not resolved:
        return None
    minimum = min(item[0] for item in resolved.values())
    best = [item[1] for item in resolved.values() if item[0] == minimum]
    return best[0] if len(best) == 1 else None


def _ordinary_row_vectors(
    page: Mapping[str, Any],
    group: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
    centers: Sequence[float],
    table_lines: Sequence[Mapping[str, Any]],
) -> list[list[dict[str, Any]]] | None:
    """Jointly bind five monotone baselines under one observed row offset."""

    if len(group) != len(_ROLES) or len(lane_types) != len(centers) or len(centers) < 2:
        return None
    center_x2 = [int(round(center * 2)) for center in centers]
    lane_gap_x2 = min(right - left for left, right in zip(center_x2, center_x2[1:], strict=False))
    tolerance_x2 = max(8, lane_gap_x2 * 2 // 5)
    numeric_lines = [
        line
        for line in table_lines
        if _line_is_numeric(line)
        and center_x2[0] - tolerance_x2 <= center_x2_v1(line) <= center_x2[-1] + tolerance_x2
    ]
    clusters = cluster_numeric_rows_v1(
        numeric_lines,
        is_numeric=_line_is_numeric,
        start_index=-1,
        stop_index=max((line["source_line_index"] for line in numeric_lines), default=0) + 1,
        page_width=_page_width(page),
        minimum_x_ratio=0.0,
        maximum_x_ratio=1.0,
    )
    baselines = []
    for cluster_lines in clusters:
        cluster = {
            "bottom": max(line["bbox"][3] for line in cluster_lines),
            "lines": list(cluster_lines),
            "top": min(line["bbox"][1] for line in cluster_lines),
        }
        vector = _cluster_vector(cluster, lane_types, centers, page)
        if vector is None:
            continue
        indices = sorted({item["source_line_index"] for item in vector})
        center_y = float(
            median(
                (page["lines"][index]["bbox"][1] + page["lines"][index]["bbox"][3]) / 2
                for index in indices
            )
        )
        baselines.append(
            {
                "center_y": center_y,
                "indices": tuple(indices),
                "vector": vector,
            }
        )
    baselines.sort(key=lambda item: (item["center_y"], item["indices"]))
    scale = median_text_height_v1(table_lines)
    # A visible owner total can sit immediately above the first grade.  It is
    # not a grade candidate, even when its baseline follows the same spacing
    # as the five grade rows.  Use the first visible grade's top as the one
    # global table-row boundary; later tall/overlapping labels may still begin
    # a few pixels below their own numeric baseline.
    first_role_top = group[0]["label"]["bbox"][1]
    baselines = [baseline for baseline in baselines if baseline["center_y"] >= first_role_top]
    options = []
    for item in group:
        label_top = item["label"]["bbox"][1]
        local = [
            (baseline, baseline["center_y"] - label_top)
            for baseline in baselines
            if -scale * 0.6 <= baseline["center_y"] - label_top <= scale * 1.25
        ]
        if not local:
            return None
        options.append(local)

    combinations: list[tuple[tuple[float, float], tuple[tuple[int, ...], ...], list[Any]]] = []

    def _extend(
        role_index: int,
        prior_center: float,
        used: set[int],
        chosen: list[Any],
        offsets: list[float],
    ) -> None:
        if role_index == len(options):
            shared_offset = float(median(offsets))
            dispersion = sum(abs(offset - shared_offset) for offset in offsets)
            span = max(offsets) - min(offsets)
            signature = tuple(item[0]["indices"] for item in chosen)
            combinations.append(((dispersion, span), signature, list(chosen)))
            return
        for baseline, offset in options[role_index]:
            indices = set(baseline["indices"])
            if baseline["center_y"] <= prior_center or indices & used:
                continue
            _extend(
                role_index + 1,
                baseline["center_y"],
                used | indices,
                [*chosen, (baseline, offset)],
                [*offsets, offset],
            )

    _extend(0, float("-inf"), set(), [], [])
    if not combinations:
        return None
    best_score = min(item[0] for item in combinations)
    best = {item[1]: item for item in combinations if item[0] == best_score}
    if len(best) != 1:
        return None
    selected = next(iter(best.values()))[2]
    return [item[0]["vector"] for item in selected]


def _bind_value_provenance(
    page: Mapping[str, Any],
    vector: Sequence[Mapping[str, Any]],
    *,
    block_ordinal: int | None,
    role: str,
) -> list[dict[str, Any]]:
    """Keep every reader surface and its exact semantic graph coordinates."""

    bound: list[dict[str, Any]] = []
    for raw_item in vector:
        item = canonical_clone_v1(raw_item)
        index = item["source_line_index"]
        line = page["lines"][index]
        item.update(
            {
                "block_ordinal": block_ordinal,
                "page_sequence": page["page_sequence"],
                "role": role,
                "source_line_surface": line["source_text"],
                "source_surface": (
                    item["surface"]
                    if item.get("source_authoritative") is True
                    else line["source_text"]
                ),
                "vietocr_line_surface": line["vietocr_text"],
                "vietocr_surface": item["semantic_surface"],
            }
        )
        bound.append(item)
    return bound


def _embedded_money_tokens(
    page: Mapping[str, Any], indices: Sequence[int], reader: str
) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for index in indices:
        surface = page["lines"][index][reader]
        if type(surface) is not str:
            continue
        for match in _MONEY_BEFORE_UNIT.finditer(surface):
            token = match.group("value").strip()
            if money_integer_v1(token) is None:
                continue
            tokens.append(
                {
                    "full_surface": surface,
                    "source_line_index": index,
                    "token": token,
                }
            )
    return tokens


def _excluded_footnote_values(
    page: Mapping[str, Any],
    label: Mapping[str, Any],
    lane_types: Sequence[str],
    centers: Sequence[float],
) -> list[dict[str, Any]]:
    money_lanes = [
        lane_index for lane_index, lane_type in enumerate(lane_types) if lane_type == "MONEY"
    ]
    source = _embedded_money_tokens(page, label["source_line_indices"], "source_text")
    semantic = _embedded_money_tokens(page, label["source_line_indices"], "vietocr_text")
    if len(source) != len(money_lanes) and len(semantic) != len(money_lanes):
        return []
    structural = semantic if len(semantic) == len(money_lanes) else source
    values = []
    for token_ordinal, (lane_index, structural_item) in enumerate(
        zip(money_lanes, structural, strict=True)
    ):
        source_item = source[token_ordinal] if len(source) == len(money_lanes) else None
        semantic_item = semantic[token_ordinal] if len(semantic) == len(money_lanes) else None
        source_authoritative = (
            page["primary_numeric_authority"]
            and source_item is not None
            and money_integer_v1(source_item["token"]) is not None
        )
        semantic_surface = (
            semantic_item["token"] if semantic_item is not None else structural_item["token"]
        )
        values.append(
            {
                "block_ordinal": None,
                "embedded_token_ordinal": token_ordinal,
                "lane_index": lane_index,
                "lane_type": "MONEY",
                "page_sequence": page["page_sequence"],
                "role": "NONADDITIVE_EXCLUDED_DISCLOSURE",
                "semantic_surface": semantic_surface,
                "source_authoritative": source_authoritative,
                "source_line_index": structural_item["source_line_index"],
                "source_line_surface": (
                    source_item["full_surface"] if source_item is not None else None
                ),
                "source_reader_line_index": (
                    source_item["source_line_index"] if source_item is not None else None
                ),
                "source_surface": source_item["token"] if source_item is not None else None,
                "surface": (source_item["token"] if source_authoritative else semantic_surface),
                "vietocr_line_surface": (
                    semantic_item["full_surface"] if semantic_item is not None else None
                ),
                "vietocr_reader_line_index": (
                    semantic_item["source_line_index"] if semantic_item is not None else None
                ),
                "vietocr_surface": (semantic_item["token"] if semantic_item is not None else None),
                "x_center_x2": int(round(centers[lane_index] * 2)),
            }
        )
    return values


def _customer_loan_parent_total(
    pages: Sequence[Mapping[str, Any]],
    current_page: Mapping[str, Any],
    owner: Mapping[str, Any] | None,
    branch: Mapping[str, Any] | None,
    first_role_top: int,
    lane_types: Sequence[str],
    centers: Sequence[float],
    minimum_ratio: float,
) -> list[dict[str, Any]]:
    if (
        owner is None
        or not centers
        or len(lane_types) != len(centers)
        or any(lane_type != "MONEY" for lane_type in lane_types)
    ):
        return []
    parent_page = _page(pages, owner["page_sequence"])
    if parent_page["page_sequence"] == current_page["page_sequence"]:
        bottom = branch["bbox"][1] if branch is not None else first_role_top
    else:
        bottom = max((line["bbox"][3] for line in parent_page["lines"]), default=0) + 1
    candidates = []
    for cluster in _numeric_clusters(
        parent_page,
        bottom=bottom,
        centers=centers,
        minimum_ratio=minimum_ratio,
    ):
        if cluster["top"] < owner["bbox"][3]:
            continue
        vector = _cluster_vector(cluster, lane_types, centers, parent_page)
        if vector is not None:
            candidates.append((cluster, vector))
    if not candidates:
        return []
    _cluster, vector = max(candidates, key=lambda item: (item[0]["top"], item[0]["bottom"]))
    return _bind_value_provenance(
        parent_page,
        vector,
        block_ordinal=None,
        role="CUSTOMER_LOAN_PARENT_TOTAL",
    )


def _numeric_clusters(
    page: Mapping[str, Any],
    *,
    bottom: int,
    centers: Sequence[float] | None = None,
    minimum_ratio: float,
) -> list[dict[str, Any]]:
    lines = page["lines"]
    if not lines:
        return []
    center_axis_x2 = [] if centers is None else [int(round(center * 2)) for center in centers]
    if len(center_axis_x2) >= 2:
        outer_tolerance_x2 = max(
            8,
            min(
                right - left
                for left, right in zip(center_axis_x2, center_axis_x2[1:], strict=False)
            )
            * 2
            // 5,
        )
    else:
        outer_tolerance_x2 = 0

    def _eligible(line: Mapping[str, Any]) -> bool:
        if not _line_is_numeric(line):
            return False
        return not center_axis_x2 or (
            center_axis_x2[0] - outer_tolerance_x2
            <= center_x2_v1(line)
            <= center_axis_x2[-1] + outer_tolerance_x2
        )

    clusters = cluster_numeric_rows_v1(
        lines,
        is_numeric=_eligible,
        start_index=-1,
        stop_index=len(lines),
        page_width=_page_width(page),
        # Once a stable center axis exists, center proximity is the tighter
        # admissibility gate.  A bbox-left ratio can reject a wide first-lane
        # total even though its center is exactly aligned with that lane.
        minimum_x_ratio=0.0 if center_axis_x2 else minimum_ratio,
        maximum_x_ratio=1.0 if center_axis_x2 else 0.995,
    )
    result = []
    for cluster in clusters:
        top = min(line["bbox"][1] for line in cluster)
        cluster_bottom = max(line["bbox"][3] for line in cluster)
        if top >= bottom:
            continue
        result.append(
            {
                "bottom": cluster_bottom,
                "center_y_x2": min(line["bbox"][1] + line["bbox"][3] for line in cluster),
                "lines": list(cluster),
                "top": top,
            }
        )
    return sorted(result, key=lambda item: (item["center_y_x2"], item["top"]))


def _cluster_vector(
    cluster: Mapping[str, Any],
    lane_types: Sequence[str],
    centers: Sequence[float],
    page: Mapping[str, Any],
) -> list[dict[str, Any]] | None:
    if len(centers) < 2:
        return None
    left = min(line["bbox"][0] for line in cluster["lines"])
    if left >= 2:
        resolved = extract_row_aligned_typed_value_vector_v1(
            cluster["lines"],
            [left - 2, cluster["top"], left - 1, cluster["bottom"]],
            lane_types,
            [int(round(center * 2)) for center in centers],
            primary_numeric_authority=page["primary_numeric_authority"],
        )
        if resolved is not None:
            return resolved
    gap = min(right - left for left, right in zip(centers, centers[1:], strict=False))
    tolerance = max(4.0, gap * 0.42)
    by_lane: dict[int, Mapping[str, Any]] = {}
    for line in cluster["lines"]:
        center = center_x2_v1(line) / 2
        lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
        if abs(center - centers[lane]) > tolerance:
            continue
        if lane in by_lane:
            return None
        by_lane[lane] = line
    if set(by_lane) != set(range(len(lane_types))):
        return None
    return extract_typed_value_vector_v1(
        [by_lane[index] for index in range(len(lane_types))],
        lane_types,
        primary_numeric_authority=page["primary_numeric_authority"],
    )


def _optional_label(
    page: Mapping[str, Any], *, top: int, bottom: int, modes: Sequence[str]
) -> dict[str, Any] | None:
    lines = page["lines"]
    vertical_tolerance = median_text_height_v1(lines) * 0.5
    candidates = []
    for line in lines:
        if not top - vertical_tolerance <= line["bbox"][1] < bottom or _line_is_numeric(line):
            continue
        normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
        if not any(mode in normalized for mode in modes):
            continue
        indices = [line["source_line_index"]]
        for other in lines:
            if other["source_line_index"] == line["source_line_index"] or _line_is_numeric(other):
                continue
            if (
                line["bbox"][1] <= other["bbox"][1] < bottom
                and -median_text_height_v1(lines) * 0.5
                <= other["bbox"][1] - page["lines"][indices[-1]]["bbox"][3]
                <= median_text_height_v1(lines) * 1.5
                and other["bbox"][0] < _page_width(page) * 0.65
            ):
                indices.append(other["source_line_index"])
                if len(indices) == 3:
                    break
        indices = sorted(set(indices), key=lambda index: (lines[index]["bbox"][1], index))
        candidates.append(
            {
                "bbox": _union_bbox(lines, indices),
                "source_line_indices": indices,
                "surface": " ".join(lines[index]["vietocr_text"] for index in indices),
            }
        )
    return min(candidates, key=lambda item: item["bbox"][1]) if candidates else None


def _horizontal_accounting(
    rows: Sequence[Mapping[str, Any]],
    core_total: Sequence[Mapping[str, Any]],
    additive_row: Mapping[str, Any] | None,
    grand_total: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
) -> str:
    if not rows or any(not row["values"] for row in rows):
        return "NOT_EVALUATED_NO_COMPLETE_NUMERIC_SURFACE"
    if any(item.get("source_authoritative") is not True for row in rows for item in row["values"]):
        return "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    row_money = [money_values_v1(row["values"]) for row in rows]
    if any(value is None for value in row_money):
        return "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    typed_money = [value for value in row_money if value is not None]
    if not typed_money or any(len(value) != len(typed_money[0]) for value in typed_money):
        return "NOT_EVALUATED_NO_COMPLETE_NUMERIC_SURFACE"
    money_sums = [
        sum(value[index] for value in typed_money) for index in range(len(typed_money[0]))
    ]
    core_money = money_values_v1(core_total) if core_total else None
    if additive_row is None:
        money_ok = core_money == money_sums and not grand_total
        total_for_percent = core_total
    else:
        additive_money = money_values_v1(additive_row["values"])
        grand_money = money_values_v1(grand_total) if grand_total else None
        money_ok = (
            additive_money is not None
            and len(additive_money) == len(money_sums)
            and (not core_total or core_money == money_sums)
            and grand_money
            and len(grand_money) == len(money_sums)
            and grand_money
            == [money_sums[index] + additive_money[index] for index in range(len(money_sums))]
        )
        total_for_percent = grand_total
    percent_ok = True
    if "PERCENT" in lane_types:
        row_percent = [percentage_values_v1(row["values"]) for row in rows]
        total_percent = percentage_values_v1(total_for_percent)
        if any(value is None for value in row_percent) or total_percent is None:
            percent_ok = False
        else:
            typed_percent = [value for value in row_percent if value is not None]
            sums = [
                sum((value[index] for value in typed_percent), Decimal(0))
                for index in range(len(typed_percent[0]))
            ]
            percent_ok = total_percent == sums == [Decimal("100.00")] * len(sums)
    return (
        "CORROBORATED_GRADE_POPULATION"
        if money_ok and percent_ok
        else "VETOED_GRADE_POPULATION_MISMATCH"
    )


def _ordinary_graph(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    group: Sequence[Mapping[str, Any]],
    branch: Mapping[str, Any] | None,
    owner: Mapping[str, Any] | None,
    bottom: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    numeric_reasons: list[str] = []
    centers, minimum_ratio = _column_centers(page, [group], bottom)
    first_label = group[0]["label"]
    header = _header_lines(page, branch, first_label)
    centers = _centers_supported_by_visible_units(header, centers)
    periods, period_mode, lane_types, unit_scope, axis_reasons = _horizontal_axes(
        pages, page, header, centers, first_label["bbox"][1]
    )
    reasons.extend(axis_reasons)
    if len(centers) not in {2, 4}:
        reasons.append("ORDINARY_VALUE_LANE_COUNT_NOT_RESOLVED")
    if branch is None:
        reasons.append("LOAN_QUALITY_BRANCH_NOT_RESOLVED")
    if owner is None:
        reasons.append("CUSTOMER_LOAN_OWNER_NOT_RESOLVED")
    table_top = max(
        0,
        min(item["label"]["bbox"][1] for item in group)
        - int(round(median_text_height_v1(page["lines"]))),
    )
    table_lines = _table_lines_by_y(page, top=table_top, bottom=bottom)
    joint_vectors = (
        _ordinary_row_vectors(page, group, lane_types, centers, table_lines)
        if lane_types and len(lane_types) == len(centers)
        else None
    )
    rows = []
    used_value_indices: set[int] = set()
    for row_ordinal, item in enumerate(group):
        vector = (
            joint_vectors[row_ordinal]
            if joint_vectors is not None
            else _row_vector(
                page, item["label"], lane_types, centers, table_lines, used_value_indices
            )
            if lane_types and len(lane_types) == len(centers)
            else None
        )
        if vector is None:
            reasons.append(f"{item['role']}_VALUE_LANES_NOT_RESOLVED")
            vector = []
        used_value_indices.update(value["source_line_index"] for value in vector)
        vector = _bind_value_provenance(page, vector, block_ordinal=None, role=item["role"])
        rows.append(
            {
                "label": canonical_clone_v1(item["label"]),
                "role": item["role"],
                "values": vector,
            }
        )

    nonadditive_rows: list[dict[str, Any]] = []
    for offset, item in enumerate(group[:-1]):
        next_top = group[offset + 1]["label"]["bbox"][1]
        label = _optional_label(
            page,
            top=item["label"]["bbox"][3],
            bottom=next_top,
            modes=("trong do",),
        )
        if label is None:
            continue
        vector = (
            _row_vector(
                page,
                label,
                lane_types,
                centers,
                table_lines,
                used_value_indices,
            )
            if lane_types
            else None
        )
        vector = _bind_value_provenance(
            page,
            vector or [],
            block_ordinal=None,
            role="NONADDITIVE_INCLUDED_DISCLOSURE",
        )
        nonadditive_rows.append(
            {
                "classification": "NONADDITIVE_INCLUDED_DISCLOSURE",
                "label_source_line_indices": label["source_line_indices"],
                "label_surface": label["surface"],
                "parent_role": item["role"],
                "values": vector,
            }
        )
        used_value_indices.update(value["source_line_index"] for value in vector)

    loss_bottom = group[-1]["label"]["bbox"][3]
    additive_label = _optional_label(
        page,
        top=loss_bottom,
        bottom=bottom,
        modes=("margin", "ky quy", "ung truoc"),
    )
    excluded_label = _optional_label(
        page,
        top=loss_bottom,
        bottom=bottom,
        modes=("khong bao gom",),
    )
    if excluded_label is not None:
        excluded_surface = normalize_vietnamese_anchor_v1(excluded_label["surface"])
        if not any(token in excluded_surface for token in ("margin", "ky quy", "ung truoc")):
            excluded_label = None
    additive_row: dict[str, Any] | None = None
    if additive_label is not None and (
        excluded_label is None or additive_label["bbox"][1] < excluded_label["bbox"][1]
    ):
        vector = _row_vector(
            page,
            additive_label,
            lane_types,
            centers,
            table_lines,
            used_value_indices,
        )
        if vector is None:
            reasons.append("ADDITIVE_MARGIN_OR_ADVANCE_VALUES_NOT_RESOLVED")
            vector = []
        vector = _bind_value_provenance(
            page,
            vector,
            block_ordinal=None,
            role="ADDITIVE_MARGIN_OR_ADVANCE_CHILD",
        )
        additive_row = {
            "classification": "ADDITIVE_MARGIN_OR_ADVANCE_CHILD",
            "label_source_line_indices": additive_label["source_line_indices"],
            "label_surface": additive_label["surface"],
            "values": vector,
        }
        used_value_indices.update(value["source_line_index"] for value in vector)
    if excluded_label is not None:
        excluded_values = _excluded_footnote_values(page, excluded_label, lane_types, centers)
        nonadditive_rows.append(
            {
                "classification": "NONADDITIVE_EXCLUDED_DISCLOSURE",
                "context_disposition": (
                    "EXPLICIT_EXCLUDED_FOOTNOTE_RECONCILES_CORE_TO_CUSTOMER_LOAN_PARENT"
                ),
                "label_source_line_indices": excluded_label["source_line_indices"],
                "label_surface": excluded_label["surface"],
                "parent_role": None,
                "values": excluded_values,
            }
        )
        used_value_indices.update(value["source_line_index"] for value in excluded_values)

    period_indices = {
        index for period in periods for index in period["evidence_source_line_indices"]
    }
    clusters = _numeric_clusters(page, bottom=bottom, centers=centers, minimum_ratio=minimum_ratio)
    complete = []
    for cluster in clusters:
        indices = {line["source_line_index"] for line in cluster["lines"]}
        if indices & used_value_indices or indices & period_indices:
            continue
        vector = _cluster_vector(cluster, lane_types, centers, page) if lane_types else None
        if vector is not None:
            complete.append((cluster, vector))
    first_top = group[0]["label"]["bbox"][1]
    vertical_tolerance = median_text_height_v1(page["lines"]) * 0.5
    leading = [
        (cluster, vector)
        for cluster, vector in complete
        if cluster["top"] < first_top and cluster["bottom"] <= first_top + vertical_tolerance
    ]
    loss_value_centers = [
        (
            page["lines"][value["source_line_index"]]["bbox"][1]
            + page["lines"][value["source_line_index"]]["bbox"][3]
        )
        / 2
        for value in rows[-1]["values"]
    ]
    loss_value_center = float(median(loss_value_centers)) if loss_value_centers else None
    trailing = [
        (cluster, vector)
        for cluster, vector in complete
        if (
            cluster["center_y_x2"] / 2 > loss_value_center
            if loss_value_center is not None
            else cluster["top"] >= loss_bottom - vertical_tolerance
        )
    ]
    core_total: list[dict[str, Any]] = []
    grand_total: list[dict[str, Any]] = []
    customer_loan_parent_total: list[dict[str, Any]] = []
    if additive_row is None:
        if trailing:
            core_total = _bind_value_provenance(
                page,
                trailing[0][1],
                block_ordinal=None,
                role="CORE_TOTAL",
            )
        elif leading:
            core_total = _bind_value_provenance(
                page,
                leading[-1][1],
                block_ordinal=None,
                role="CORE_TOTAL",
            )
        else:
            reasons.append("CORE_TOTAL_NOT_RESOLVED")
    else:
        additive_top = additive_label["bbox"][1] if additive_label is not None else loss_bottom
        before_additive = [vector for cluster, vector in trailing if cluster["top"] < additive_top]
        after_additive = [
            vector
            for cluster, vector in trailing
            if cluster["top"]
            >= (additive_label["bbox"][3] - vertical_tolerance if additive_label else additive_top)
        ]
        if before_additive:
            core_total = _bind_value_provenance(
                page,
                before_additive[-1],
                block_ordinal=None,
                role="CORE_TOTAL",
            )
        if after_additive:
            grand_total = _bind_value_provenance(
                page,
                after_additive[0],
                block_ordinal=None,
                role="GRAND_TOTAL",
            )
        else:
            reasons.append("GRAND_TOTAL_NOT_RESOLVED")

    if excluded_label is not None:
        customer_loan_parent_total = _customer_loan_parent_total(
            pages,
            page,
            owner,
            branch,
            first_top,
            lane_types,
            centers,
            minimum_ratio,
        )

    arithmetic = _horizontal_accounting(rows, core_total, additive_row, grand_total, lane_types)
    if arithmetic.startswith("VETOED"):
        numeric_reasons.append("ARITHMETIC_POPULATION_VETO_REQUIRES_NUMERIC_RECONCILIATION")
    elif arithmetic.startswith("NOT_EVALUATED"):
        numeric_reasons.append(arithmetic)
    structural = not reasons
    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if structural and arithmetic == "CORROBORATED_GRADE_POPULATION"
        else "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        if structural
        else "UNRESOLVED"
    )
    return {
        "arithmetic_status": arithmetic,
        "axes": periods,
        "branch": canonical_clone_v1(branch),
        "lane_centers_x2": [int(round(center * 2)) for center in centers],
        "lane_types": lane_types,
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "nonadditive_rows": nonadditive_rows,
        "numeric_unresolved_reasons": sorted(set(numeric_reasons)),
        "optional_additive_row": additive_row,
        "owner_context": canonical_clone_v1(owner),
        "page_sequence": page["page_sequence"],
        "period_mode": period_mode,
        "rows": rows,
        "status": status,
        "totals": {
            "core": core_total,
            "customer_loan_parent": customer_loan_parent_total,
            "grand": grand_total,
        },
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }


def _header_anchor(
    page: Mapping[str, Any], *, before_top: int, aliases: Sequence[str]
) -> dict[str, Any] | None:
    lines = [line for line in page["lines"] if line["bbox"][1] < before_top]
    direct = [
        line
        for line in lines
        if match_vietnamese_anchor_alias_v1(line["vietocr_text"], aliases) is not None
    ]
    if direct:
        line = max(direct, key=lambda item: item["bbox"][1])
        return {
            "bbox": canonical_clone_v1(line["bbox"]),
            "source_line_indices": [line["source_line_index"]],
            "surface": line["vietocr_text"],
            "x_center_x2": center_x2_v1(line),
        }
    normalized_aliases = {normalize_vietnamese_anchor_v1(alias) for alias in aliases}
    candidates = []
    for left in lines:
        for right in lines:
            if left is right:
                continue
            if abs((left["bbox"][1] + left["bbox"][3]) - (right["bbox"][1] + right["bbox"][3])) < 8:
                continue
            surface = f"{left['vietocr_text']} {right['vietocr_text']}"
            if normalize_vietnamese_anchor_v1(surface) not in normalized_aliases:
                continue
            if abs(center_x2_v1(left) - center_x2_v1(right)) > max(
                left["bbox"][2] - left["bbox"][0], right["bbox"][2] - right["bbox"][0]
            ):
                continue
            indices = sorted([left["source_line_index"], right["source_line_index"]])
            candidates.append(
                {
                    "bbox": _union_bbox(page["lines"], indices),
                    "source_line_indices": indices,
                    "surface": surface,
                    "x_center_x2": (center_x2_v1(left) + center_x2_v1(right)) // 2,
                }
            )
    return max(candidates, key=lambda item: item["bbox"][1]) if candidates else None


def _stacked_row_values(
    page: Mapping[str, Any],
    label: Mapping[str, Any],
    centers: Sequence[float],
    table_lines: Sequence[Mapping[str, Any]],
    minimum_ratio: float,
    excluded_source_line_indices: set[int] | None = None,
) -> list[dict[str, Any]]:
    boxes = [page["lines"][index]["bbox"] for index in label["source_line_indices"]]
    attempts = [boxes, *[[box] for box in reversed(boxes)]]
    center_x2 = [int(round(center * 2)) for center in centers]
    lane_gap_x2 = min(right - left for left, right in zip(center_x2, center_x2[1:], strict=False))
    tolerance_x2 = max(8, lane_gap_x2 * 2 // 5)
    available = [
        line
        for line in table_lines
        if line["source_line_index"] not in (excluded_source_line_indices or set())
        and _line_is_numeric(line)
        and center_x2[0] - tolerance_x2 <= center_x2_v1(line) <= center_x2[-1] + tolerance_x2
    ]
    clusters = cluster_numeric_rows_v1(
        available,
        is_numeric=_line_is_numeric,
        start_index=-1,
        stop_index=max((line["source_line_index"] for line in available), default=0) + 1,
        page_width=_page_width(page),
        minimum_x_ratio=0.0,
        maximum_x_ratio=1.0,
    )
    resolved: dict[tuple[int, ...], tuple[float, list[dict[str, Any]]]] = {}
    for label_boxes in attempts:
        for cluster in clusters:
            assignments = assign_value_row_lanes_v1(
                cluster,
                label_boxes=label_boxes,
                is_numeric=_line_is_numeric,
                page_width=_page_width(page),
                minimum_x_ratio=minimum_ratio,
                maximum_x_ratio=0.995,
                resolved_column_centers=tuple(float(center) for center in centers),
            )
            vector = []
            affinities = []
            for assignment in assignments:
                singleton = extract_typed_value_vector_v1(
                    [assignment["line"]],
                    ["MONEY"],
                    primary_numeric_authority=page["primary_numeric_authority"],
                )
                if singleton is None:
                    continue
                item = singleton[0]
                item["lane_index"] = assignment["column_ordinal"]
                vector.append(item)
                affinities.append(assignment["row_affinity"])
            vector.sort(key=lambda item: item["lane_index"])
            if not vector:
                continue
            signature = tuple(item["source_line_index"] for item in vector)
            score = float(median(affinities))
            current = resolved.get(signature)
            if current is None or score > current[0]:
                resolved[signature] = (score, vector)
    if not resolved:
        return []
    maximum = max(score for score, _vector in resolved.values())
    best = [vector for score, vector in resolved.values() if score == maximum]
    return best[0] if len(best) == 1 else []


def _period_for_blocks(
    page: Mapping[str, Any],
    groups: Sequence[Sequence[Mapping[str, Any]]],
    branch: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    before_first = _header_lines(page, branch, groups[0][0]["label"])
    try:
        initial = extract_period_observations_v1(before_first)
    except AccountingTableAxesV1Error:
        initial = []
    between: list[list[dict[str, Any]]] = []
    for offset in range(1, len(groups)):
        prior_bottom = groups[offset - 1][-1]["label"]["bbox"][3]
        current_top = groups[offset][0]["label"]["bbox"][1]
        header = [
            _period_line(line, page)
            for line in page["lines"]
            if line["bbox"][1] >= prior_bottom and line["bbox"][3] <= current_top
        ]
        try:
            between.append(extract_period_observations_v1(header))
        except AccountingTableAxesV1Error:
            between.append([])
    selected: list[dict[str, Any]] = []
    if len(groups) == 2 and initial and between and between[0]:
        selected = [initial[-1], between[0][-1]]
        mode = "LOCAL_PERIOD_OBSERVATION_PER_STACKED_BLOCK"
    elif len(groups) == 2 and len(initial) == 2 and between and not between[0]:
        selected = initial
        mode = "LOCAL_TWO_PERIOD_HEADER_FOR_STACKED_BLOCKS"
    else:
        mode = "UNRESOLVED"
    public = [
        {
            key: canonical_clone_v1(value)
            for key, value in item.items()
            if key != "source_line_index"
        }
        for item in selected
    ]
    return public, mode


def _stacked_accounting(
    blocks: Sequence[Mapping[str, Any]],
    column_count: int,
    target_column: int | None,
    total_column: int | None,
) -> tuple[str, dict[str, Any]]:
    """Evaluate required and optional stacked equations without blank-as-zero.

    The customer-loan target column is the one required family equation.  A
    companion column or a row-total equation is evaluated only when every
    operand is visibly present.  Sparse presentation blanks therefore remain
    explicit ``NOT_EVALUATED`` checks instead of becoming synthetic zeroes.
    """

    checks: dict[str, Any] = {
        "companion_column_checks": [],
        "policy": "REQUIRED_TARGET_COLUMN_OPTIONAL_COMPLETE_COMPANION_AND_ROW_TOTALS_NO_BLANK_AS_ZERO",
        "row_total_checks": [],
        "target_column_checks": [],
    }
    if len(blocks) != 2 or target_column is None or total_column is None:
        return "NOT_EVALUATED_NO_COMPLETE_NUMERIC_SURFACE", checks

    def _visible_values(vector: Sequence[Mapping[str, Any]]) -> tuple[dict[int, int], set[int]]:
        values: dict[int, int] = {}
        unauthoritative: set[int] = set()
        for item in vector:
            lane = item["lane_index"]
            parsed = money_values_v1([item])
            if parsed is None:
                unauthoritative.add(lane)
                continue
            values[lane] = parsed[0]
        return values, unauthoritative

    vetoed = False
    target_not_evaluated: list[str] = []
    for block in blocks:
        row_values: list[dict[int, int]] = []
        row_unauthoritative: list[set[int]] = []
        for row in block["rows"]:
            visible, unauthoritative = _visible_values(row["values"])
            row_values.append(visible)
            row_unauthoritative.append(unauthoritative)
        total_values, total_unauthoritative = _visible_values(block["total"])

        target_present = all(
            target_column in visible or target_column in unauthoritative
            for visible, unauthoritative in zip(row_values, row_unauthoritative, strict=True)
        ) and (target_column in total_values or target_column in total_unauthoritative)
        target_authoritative = (
            target_present
            and all(target_column not in lanes for lanes in row_unauthoritative)
            and target_column not in total_unauthoritative
        )
        if not target_present:
            target_state = "NOT_EVALUATED_INCOMPLETE_REQUIRED_TARGET_COLUMN"
        elif not target_authoritative:
            target_state = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
        elif sum(row[target_column] for row in row_values) == total_values[target_column]:
            target_state = "CORROBORATED"
        else:
            target_state = "VETOED_MISMATCH"
            vetoed = True
        if target_state.startswith("NOT_EVALUATED"):
            target_not_evaluated.append(target_state)
        checks["target_column_checks"].append(
            {
                "block_ordinal": block["block_ordinal"],
                "column_index": target_column,
                "status": target_state,
            }
        )

        for column in range(column_count):
            if column in {target_column, total_column}:
                continue
            present = all(
                column in visible or column in unauthoritative
                for visible, unauthoritative in zip(row_values, row_unauthoritative, strict=True)
            ) and (column in total_values or column in total_unauthoritative)
            authoritative = (
                present
                and all(column not in lanes for lanes in row_unauthoritative)
                and column not in total_unauthoritative
            )
            if not present:
                state = "NOT_EVALUATED_INCOMPLETE_VISIBLE_COLUMN"
            elif not authoritative:
                state = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            elif sum(row[column] for row in row_values) == total_values[column]:
                state = "CORROBORATED"
            else:
                state = "VETOED_MISMATCH"
                vetoed = True
            checks["companion_column_checks"].append(
                {
                    "block_ordinal": block["block_ordinal"],
                    "column_index": column,
                    "status": state,
                }
            )

        component_columns = set(range(column_count)) - {total_column}
        for row, visible, unauthoritative in zip(
            block["rows"], row_values, row_unauthoritative, strict=True
        ):
            operands = component_columns | {total_column}
            present = all(column in visible or column in unauthoritative for column in operands)
            authoritative = present and not (operands & unauthoritative)
            if not present:
                state = "NOT_EVALUATED_INCOMPLETE_VISIBLE_ROW"
            elif not authoritative:
                state = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            elif sum(visible[column] for column in component_columns) == visible[total_column]:
                state = "CORROBORATED"
            else:
                state = "VETOED_MISMATCH"
                vetoed = True
            checks["row_total_checks"].append(
                {
                    "block_ordinal": block["block_ordinal"],
                    "role": row["role"],
                    "status": state,
                }
            )

    if vetoed:
        return "VETOED_STACKED_POPULATION_MISMATCH", checks
    if target_not_evaluated:
        status = (
            "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            if "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY" in target_not_evaluated
            else "NOT_EVALUATED_NO_COMPLETE_NUMERIC_SURFACE"
        )
        return status, checks
    return "CORROBORATED_STACKED_REQUIRED_TARGET_POPULATIONS", checks


def _stacked_graph(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    groups: Sequence[Sequence[Mapping[str, Any]]],
    branch: Mapping[str, Any] | None,
    owner: Mapping[str, Any] | None,
    bottom: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    numeric_reasons: list[str] = []
    centers, minimum_ratio = _column_centers(page, groups, bottom)
    if len(groups) != 2:
        reasons.append("EXACT_TWO_STACKED_PERIOD_BLOCKS_NOT_RESOLVED")
    if len(centers) < 3:
        reasons.append("MULTI_ASSET_COLUMN_AXIS_NOT_RESOLVED")
    first_top = groups[0][0]["label"]["bbox"][1]
    customer_header = _header_anchor(page, before_top=first_top, aliases=["Cho vay khách hàng"])
    total_header = _header_anchor(page, before_top=first_top, aliases=["Tổng cộng"])
    if customer_header is None:
        reasons.append("CUSTOMER_LOAN_TARGET_COLUMN_NOT_RESOLVED")
    if total_header is None:
        reasons.append("TOTAL_COMPANION_COLUMN_NOT_RESOLVED")
    if centers and total_header is not None:
        total_distances = [abs(center * 2 - total_header["x_center_x2"]) for center in centers]
        terminal_column = min(range(len(total_distances)), key=total_distances.__getitem__)
        if total_distances.count(total_distances[terminal_column]) == 1:
            # The visible total header is the terminal table column.  Reader
            # numerics strictly to its right are page-edge artifacts, not a
            # sixth asset lane.
            centers = centers[: terminal_column + 1]
    target_column: int | None = None
    total_column: int | None = None
    if centers and customer_header is not None:
        distances = [abs(center * 2 - customer_header["x_center_x2"]) for center in centers]
        target_column = min(range(len(distances)), key=distances.__getitem__)
        if distances.count(distances[target_column]) != 1:
            target_column = None
            reasons.append("CUSTOMER_LOAN_TARGET_COLUMN_GEOMETRY_AMBIGUOUS")
    if centers and total_header is not None:
        distances = [abs(center * 2 - total_header["x_center_x2"]) for center in centers]
        total_column = min(range(len(distances)), key=distances.__getitem__)
        if distances.count(distances[total_column]) != 1:
            total_column = None
            reasons.append("TOTAL_COLUMN_GEOMETRY_AMBIGUOUS")
    axes, period_mode = _period_for_blocks(page, groups, branch)
    if len(axes) != 2:
        reasons.append("STACKED_PERIOD_AXIS_NOT_RESOLVED")
    unit_lines = [
        line
        for line in page["lines"]
        if line["bbox"][1] < first_top and unit_kind_v1(line["vietocr_text"]) == "MONEY"
    ]
    inherited = _inherited_unit(pages, page["page_sequence"], first_top)
    if unit_lines:
        unit_scope: dict[str, Any] = {
            "mode": "LOCAL_SHARED_MONEY_UNIT",
            "source_line_indices": [line["source_line_index"] for line in unit_lines],
        }
    elif inherited is not None:
        unit_scope = {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}
    else:
        unit_scope = {"mode": "UNRESOLVED"}
        reasons.append("UNIT_SCOPE_NOT_RESOLVED")
    table_top = max(
        0,
        groups[0][0]["label"]["bbox"][1] - int(round(median_text_height_v1(page["lines"]))),
    )
    table_lines = _table_lines_by_y(page, top=table_top, bottom=bottom)
    clusters = _numeric_clusters(page, bottom=bottom, centers=centers, minimum_ratio=minimum_ratio)
    blocks = []
    for block_ordinal, group in enumerate(groups[:2]):
        rows = []
        used: set[int] = set()
        for item in group:
            vector = _stacked_row_values(
                page,
                item["label"],
                centers,
                table_lines,
                minimum_ratio,
                used,
            )
            present = {value["lane_index"] for value in vector}
            if (
                not vector
                or target_column is None
                or total_column is None
                or not {target_column, total_column}.issubset(present)
            ):
                reasons.append(f"STACKED_BLOCK_{block_ordinal}_{item['role']}_VALUES_UNRESOLVED")
                vector = []
            used.update(value["source_line_index"] for value in vector)
            vector = _bind_value_provenance(
                page,
                vector,
                block_ordinal=block_ordinal,
                role=item["role"],
            )
            rows.append(
                {
                    "label": canonical_clone_v1(item["label"]),
                    "role": item["role"],
                    "values": vector,
                }
            )
        loss_bottom = group[-1]["label"]["bbox"][3]
        next_top = (
            groups[block_ordinal + 1][0]["label"]["bbox"][1]
            if block_ordinal + 1 < len(groups)
            else bottom
        )
        totals = []
        for cluster in clusters:
            indices = {line["source_line_index"] for line in cluster["lines"]}
            if indices & used or not (
                cluster["top"] >= loss_bottom and cluster["bottom"] <= next_top
            ):
                continue
            vector = _cluster_vector(cluster, ["MONEY"] * len(centers), centers, page)
            if vector is not None:
                totals.append(vector)
        total = (
            _bind_value_provenance(
                page,
                totals[0],
                block_ordinal=block_ordinal,
                role="BLOCK_TOTAL",
            )
            if len(totals) == 1
            else []
        )
        if not total:
            reasons.append(f"STACKED_BLOCK_{block_ordinal}_TOTAL_UNRESOLVED")
        blocks.append(
            {
                "block_ordinal": block_ordinal,
                "period": axes[block_ordinal] if block_ordinal < len(axes) else None,
                "rows": rows,
                "total": total,
            }
        )
    arithmetic, accounting_checks = _stacked_accounting(
        blocks, len(centers), target_column, total_column
    )
    if arithmetic.startswith("VETOED"):
        numeric_reasons.append("ARITHMETIC_POPULATION_VETO_REQUIRES_NUMERIC_RECONCILIATION")
    elif arithmetic.startswith("NOT_EVALUATED"):
        numeric_reasons.append(arithmetic)
    if branch is None:
        reasons.append("LOAN_QUALITY_BRANCH_NOT_RESOLVED")
    if owner is None:
        reasons.append("LOAN_QUALITY_OWNER_NOT_RESOLVED")
    structural = not reasons
    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if structural and arithmetic == "CORROBORATED_STACKED_REQUIRED_TARGET_POPULATIONS"
        else "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        if structural
        else "UNRESOLVED"
    )
    return {
        "arithmetic_status": arithmetic,
        "accounting_checks": accounting_checks,
        "axes": axes,
        "blocks": blocks,
        "branch": canonical_clone_v1(branch),
        "column_centers_x2": [int(round(center * 2)) for center in centers],
        "customer_loan_column": {"column_index": target_column, "header": customer_header},
        "layout_mode": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
        "numeric_unresolved_reasons": sorted(set(numeric_reasons)),
        "owner_context": canonical_clone_v1(owner),
        "page_sequence": page["page_sequence"],
        "period_mode": period_mode,
        "status": status,
        "total_column": {"column_index": total_column, "header": total_header},
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }


def _graph_signature(graph: Mapping[str, Any]) -> str:
    material = canonical_clone_v1(graph)
    material.pop("branch", None)
    material.pop("status", None)
    material.pop("arithmetic_status", None)
    material.pop("numeric_unresolved_reasons", None)
    material.pop("unresolved_reasons", None)
    return canonical_json_sha256_v1(material)


def _build_graphs(
    pages: Sequence[Mapping[str, Any]], region_scan: Mapping[str, Any]
) -> list[dict[str, Any]]:
    topology_pages = _topology_pages(pages)
    proposals: list[dict[str, Any]] = []
    explicit_regions = [
        region
        for region in region_scan["regions"]
        if region["parent_resolution"] == "EXPLICIT_PARENT"
    ]
    # A visible family heading is stronger than unheaded five-grade role
    # lists elsewhere in the document (for example narrative policy lists).
    # Implied clusters remain available only when no explicit family region
    # exists anywhere in the complete document.
    candidate_regions = explicit_regions or region_scan["regions"]
    maximal_regions = []
    for region in candidate_regions:
        start = region["cluster_start_document_line_ordinal"]
        stop = region["cluster_end_document_line_ordinal_exclusive"]
        numeric_stop = 10**18 if stop is None else stop
        contained = any(
            other["page_sequence"] == region["page_sequence"]
            and other["cluster_start_document_line_ordinal"] <= start
            and (
                10**18
                if other["cluster_end_document_line_ordinal_exclusive"] is None
                else other["cluster_end_document_line_ordinal_exclusive"]
            )
            >= numeric_stop
            and (
                other["cluster_start_document_line_ordinal"] < start
                or (
                    other["cluster_end_document_line_ordinal_exclusive"] is None
                    and stop is not None
                )
                or (
                    other["cluster_end_document_line_ordinal_exclusive"] is not None
                    and stop is not None
                    and other["cluster_end_document_line_ordinal_exclusive"] > stop
                )
            )
            for other in candidate_regions
        )
        if not contained:
            maximal_regions.append(region)
    unique_regions = {canonical_json_sha256_v1(region): region for region in maximal_regions}
    for region in unique_regions.values():
        try:
            occurrences = enumerate_accounting_family_role_occurrences_v1(
                topology_pages, LOAN_QUALITY_TOPOLOGY_SPEC_V2, region
            )
        except AccountingFamilyTopologyV1Error:
            # The shared accessor deliberately rejects a scan containing two
            # byte-identical complete regions.  Those are not independently
            # bindable evidence candidates, so fail closed and retain neither.
            continue
        candidate_pages = sorted({item["page_sequence"] for item in occurrences})
        for page_sequence in candidate_pages:
            page = _page(pages, page_sequence)
            labels = _visual_labels(page, occurrences)
            if not labels:
                continue
            first_top = labels[0]["label"]["bbox"][1]
            bottom = _table_bottom_y(page, labels, first_role_top=first_top)
            labels = [item for item in labels if item["label"]["bbox"][1] < bottom]
            groups = _role_groups(labels)
            if not groups:
                continue
            branch_alternatives = _branch_candidates(
                page, first_role_top=groups[0][0]["label"]["bbox"][1]
            )
            branch = branch_alternatives[-1] if branch_alternatives else None
            owner = _owner_context(pages, page, groups[0][0]["label"]["bbox"][1])
            graph = (
                _stacked_graph(pages, page, groups, branch, owner, bottom)
                if len(groups) >= 2
                else _ordinary_graph(pages, page, groups[0], branch, owner, bottom)
            )
            graph["branch_alternative_count"] = len(branch_alternatives)
            graph["table_bottom_y"] = bottom
            proposals.append(graph)
    deduplicated: dict[str, dict[str, Any]] = {}
    for graph in proposals:
        signature = _graph_signature(graph)
        current = deduplicated.get(signature)
        if current is None:
            deduplicated[signature] = graph
            continue
        current_branch = current.get("branch")
        branch = graph.get("branch")
        current_top = -1 if current_branch is None else current_branch["bbox"][1]
        branch_top = -1 if branch is None else branch["bbox"][1]
        if branch_top > current_top:
            deduplicated[signature] = graph
    return sorted(
        deduplicated.values(),
        key=lambda graph: (
            graph["page_sequence"],
            graph["layout_mode"],
            _graph_signature(graph),
        ),
    )


def _metrics(graphs: Sequence[Mapping[str, Any]], region_scan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "accepted_graph_count": sum(
            graph["status"] == "ACCEPTED_VARIANT_GRAPH" for graph in graphs
        ),
        "complete_anchor_region_count": len(graphs),
        "exact_duplicate_candidate_count": max(
            0, region_scan["metrics"]["complete_region_count"] - len(graphs)
        ),
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


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-quality V2 document graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or type(value["graphs"]) is not list
        or type(value["region_scan"]) is not dict
        or not same_typed_json_v1(value["safety"], _SAFETY)
    ):
        raise _error("loan-quality V2 document graph identity/safety drifted")
    expected_metrics = _metrics(value["graphs"], value["region_scan"])
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("loan-quality V2 document graph metrics drifted")
    count = expected_metrics["structurally_resolved_graph_count"]
    uniqueness = {
        "full_match_count": count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if count == 1
            else "MULTIPLE_FULL_MATCHES"
            if count > 1
            else "NO_FULL_MATCH"
        ),
    }
    if not same_typed_json_v1(value["uniqueness"], uniqueness):
        raise _error("loan-quality V2 document uniqueness evidence drifted")
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if count == 1 and expected_metrics["accepted_graph_count"] == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if not value["graphs"]
        else "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    )
    if value["status"] != expected_status:
        raise _error("loan-quality V2 document status drifted")
    for graph in value["graphs"]:
        if graph.get("layout_mode") == "HORIZONTAL_TYPED_PERIOD_LANES":
            if [row.get("role") for row in graph.get("rows", [])] != list(_ROLES):
                raise _error("loan-quality V2 horizontal role axis drifted")
        elif graph.get("layout_mode") == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS":
            if any(
                [row.get("role") for row in block.get("rows", [])] != list(_ROLES)
                for block in graph.get("blocks", [])
            ):
                raise _error("loan-quality V2 stacked role axis drifted")
        else:
            raise _error("loan-quality V2 layout mode drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lqvgv2:document:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality V2 document identity drifted")
    return canonical_clone_v1(value)


def build_loan_quality_variant_graph_document_v2(
    document_pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_annual_variants: bool = False,
) -> dict[str, Any]:
    """Enumerate V2 loan-quality graphs from one complete document.

    ``enable_extended_annual_variants`` remains in the public shape used by
    V1 callers.  V2's declarative topology is layout-general, so both flag
    values intentionally execute the same rules.
    """

    if type(enable_extended_annual_variants) is not bool:
        raise _error("loan-quality V2 annual-variant flag drifted")
    pages = _pages(document_pages)
    region_scan = build_accounting_family_topology_scan_v1(
        _topology_pages(pages), LOAN_QUALITY_TOPOLOGY_SPEC_V2
    )
    graphs = _build_graphs(pages, region_scan)
    metrics = _metrics(graphs, region_scan)
    count = metrics["structurally_resolved_graph_count"]
    uniqueness = {
        "full_match_count": count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if count == 1
            else "MULTIPLE_FULL_MATCHES"
            if count > 1
            else "NO_FULL_MATCH"
        ),
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": metrics,
        "region_scan": region_scan,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if count == 1 and metrics["accepted_graph_count"] == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not graphs
            else "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
        ),
        "uniqueness": uniqueness,
    }
    return _validate_result(
        {
            **material,
            "result_id": "lqvgv2:document:" + canonical_json_sha256_v1(material),
        }
    )


def validate_loan_quality_variant_graph_document_v2(value: Any) -> dict[str, Any]:
    """Validate one self-identifying V2 graph document without rebuilding it."""

    return _validate_result(value)


def validate_loan_quality_variant_graph_replay_v2(
    value: Any,
    document_pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_annual_variants: bool = False,
) -> dict[str, Any]:
    """Exact-rebuild a V2 graph from the complete immutable line axis."""

    persisted = _validate_result(value)
    rebuilt = build_loan_quality_variant_graph_document_v2(
        document_pages,
        enable_extended_annual_variants=enable_extended_annual_variants,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-quality V2 document graph does not replay exactly")
    return rebuilt
