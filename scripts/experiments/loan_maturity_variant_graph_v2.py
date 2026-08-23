"""Bank-blind V2 graph for customer-loan maturity buckets.

The complete PDF is searched by semantic topology first.  Numeric geometry is
then solved only inside the unique shortlisted region.  Provider line order is
never treated as table order: the three bucket rows are assigned jointly from
visual numeric baselines and the winning assignment must close the printed
core/grand total equations.

The module intentionally contains no bank, filename, page, note, year, or
reporting-period routing.  Qualified bucket wording, optional ``Dư nợ cho
vay``, margin/advance rows, and percentage companions are family variants.
Topology may flag a one-page continuation candidate, but an accepted numeric
graph currently requires all three core labels on one page.  VietOCR remains
semantic evidence; bound PP-OCR text is preserved as the primary numeric
proposal and conflicts remain unresolved for an independent challenger.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from itertools import combinations
from statistics import median
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    SPEC_FORMAT_VERSION,
    build_accounting_family_topology_scan_v1,
)
from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    center_x2_v1,
    extract_period_axis_v1,
    extract_typed_value_vector_v1,
    line_has_accounting_value_surface_v1,
    money_integer_v1,
    money_values_v1,
    percentage_values_v1,
    unit_kind_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
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
    "FAMILY_ID",
    "FORMAT_VERSION",
    "LOAN_MATURITY_TOPOLOGY_SPEC_V2",
    "LoanMaturityVariantGraphV2Error",
    "build_loan_maturity_variant_graph_from_topology_scan_v2",
    "build_loan_maturity_variant_graph_document_v2",
    "validate_loan_maturity_variant_graph_document_v2",
    "validate_loan_maturity_variant_graph_replay_v2",
]


FORMAT_VERSION = "LOAN_MATURITY_VARIANT_GRAPH_DOCUMENT_V2"
FAMILY_ID = "LOAN_MATURITY_BUCKETS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_DOCUMENT_FRESH_VIETOCR_BOUND_PPOCR_NUMERIC_"
    "OWNER_BRANCH_CHILD_VISUAL_BASELINE_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_"
    "PROPOSAL_ONLY_NO_SCHEMA_MAPPING_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
_ROLE_ALIASES = {
    "SHORT_TERM": (
        "Nợ ngắn hạn",
        "Cho vay ngắn hạn",
        "Ngắn hạn",
        "Nợ ngắn hạn (đến 01 năm)",
        "Nợ ngắn hạn (đến 1 năm)",
        "Nợ ngắn hạn (dưới 1 năm)",
    ),
    "MEDIUM_TERM": (
        "Nợ trung hạn",
        "Cho vay trung hạn",
        "Trung hạn",
        "Nợ trung hạn (trên 01 đến 05 năm)",
        "Nợ trung hạn (trên 01 đến 5 năm)",
        "Nợ trung hạn (từ 1 tới 5 năm)",
    ),
    "LONG_TERM": (
        "Nợ dài hạn",
        "Cho vay dài hạn",
        "Dài hạn",
        "Nợ dài hạn (trên 05 năm)",
        "Nợ dài hạn (trên 5 năm)",
    ),
}
_BRANCH_ALIASES = (
    "Phân tích dư nợ theo thời gian",
    "Phân tích dư nợ theo thời gian cho vay ban đầu",
    "Phân tích dư nợ theo thời gian cho vay gốc",
    "Phân tích dư nợ theo thời gian gốc của khoản vay",
    "Phân tích dư nợ theo thời gian đáo hạn",
    "Phân tích dư nợ cho vay theo thời gian",
    "Phân tích dư nợ theo thời gian cho vay",
    "Phân tích dư nợ cho vay theo thời hạn gốc của khoản vay",
    "Phân tích dư nợ theo thời hạn cho vay",
    "Phân tích dư nợ theo thời hạn cho vay như sau",
    "Phân tích dư nợ cho vay theo thời hạn vay",
    "Theo kỳ hạn",
)
_OWNER_ALIASES = (
    "Cho vay khách hàng",
    "Các khoản cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
)
_RESET_ALIASES = (
    "Phân tích chất lượng nợ cho vay",
    "Phân tích chất lượng dư nợ cho vay",
    "Phân tích dư nợ theo chất lượng nợ",
    "Phân tích dư nợ theo ngành",
    "Phân tích dư nợ cho vay theo ngành",
    "Phân tích dư nợ theo ngành nghề kinh tế",
    "Phân tích dư nợ theo đối tượng khách hàng",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng",
    "Dự phòng rủi ro cho vay khách hàng",
)
_HARD_NEGATIVES = (
    "Phân tích rủi ro thanh khoản",
    "Rủi ro thanh khoản",
    "Phân tích rủi ro lãi suất",
    "Rủi ro lãi suất",
)

LOAN_MATURITY_TOPOLOGY_SPEC_V2 = {
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
    "hard_negative_aliases": list(_HARD_NEGATIVES),
    "limits": {
        "max_cluster_span_lines": 160,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    },
    "parent": {
        "aliases": list(_BRANCH_ALIASES),
        "resolution_mode": "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER",
        "role": "LOAN_MATURITY_BRANCH",
    },
    "structural_reset_aliases": list(_RESET_ALIASES),
}

_SAFETY = {
    "bank_filename_note_page_or_period_used_for_inference": False,
    "blank_or_omitted_dash_synthesized_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "numeric_conflict_silently_corrected": False,
    "numeric_authority_requires_bound_source_surface": True,
    "parent_plus_one_child_combination_tested_first": True,
    "percentage_companion_lanes_silently_discarded": False,
    "persisted_result_self_authenticating": False,
    "provider_line_order_used_as_table_order": False,
    "public_exact_replay_required": True,
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
_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_SECTION_PREFIX = re.compile(r"^\d{1,3}(?:\s+\d{1,3}){0,2}\s+")


class LoanMaturityVariantGraphV2Error(ValueError):
    """The complete-document maturity graph input or replay drifted."""


def _error(message: str) -> LoanMaturityVariantGraphV2Error:
    return LoanMaturityVariantGraphV2Error(message)


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
        raise _error("maturity V2 requires one non-empty complete PDF page sequence")
    pages = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("maturity V2 page fields drifted")
        if (
            raw_page["page_sequence"] != page_offset + 1
            or type(raw_page["primary_numeric_authority"]) is not bool
            or type(raw_page["lines"]) is not list
        ):
            raise _error("maturity V2 page identity or authority drifted")
        lines = []
        for line_offset, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("maturity V2 line fields drifted")
            if (
                raw_line["source_line_index"] != line_offset
                or type(raw_line["vietocr_text"]) is not str
                or (
                    raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str
                )
            ):
                raise _error("maturity V2 line identity/text drifted")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], "maturity V2 line"),
                    "source_line_index": line_offset,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_offset + 1,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
    return pages


def _topology_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": canonical_clone_v1(page["lines"]),
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]


def _union_bbox(lines: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> list[int]:
    boxes = [lines[index]["bbox"] for index in indices]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _indices(match: Mapping[str, Any]) -> list[int]:
    explicit = match.get("source_line_indices")
    if explicit is not None:
        return list(explicit)
    return list(range(match["source_line_index"], match["end_source_line_index"] + 1))


def _branch_like(surface: str) -> bool:
    normalized = normalize_vietnamese_anchor_v1(surface)
    if normalized == "theo ky han":
        return True
    return (
        "phan tich" in normalized
        and "du no" in normalized
        and ("thoi gian" in normalized or "thoi han" in normalized or "ky han" in normalized)
    )


def _branch_variant(surface: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(surface)
    if "dao han" in normalized:
        return "MATURITY_TIME_WORDING"
    if "ky han" in normalized:
        return "TENOR_WORDING"
    if "ban dau" in normalized:
        return "INITIAL_TERM_WORDING"
    if "goc" in normalized:
        return "ORIGINAL_TERM_WORDING"
    if "thoi han" in normalized:
        return "TERM_WORDING"
    return "TIME_WORDING"


def _branch(
    page: Mapping[str, Any], region: Mapping[str, Any], *, first_label_top: int
) -> dict[str, Any] | None:
    lines = page["lines"]
    match = region["parent_match"]
    if match is not None:
        indices = _indices(match)
        return {
            "bbox": _union_bbox(lines, indices),
            "match_kind": match["match_kind"],
            "resolution": region["parent_resolution"],
            "source_line_indices": indices,
            "surface": match["surface"],
            "variant": _branch_variant(match["surface"]),
        }
    candidates = [
        line
        for line in lines
        if line["bbox"][1] < first_label_top and _branch_like(line["vietocr_text"])
    ]
    if not candidates:
        return None
    selected = max(candidates, key=lambda line: (line["bbox"][1], line["source_line_index"]))
    return {
        "bbox": canonical_clone_v1(selected["bbox"]),
        "match_kind": "BOUNDED_BRANCH_PHRASE_IN_UNIQUE_REQUIRED_CHILD_CLUSTER",
        "resolution": region["parent_resolution"],
        "source_line_indices": [selected["source_line_index"]],
        "surface": selected["vietocr_text"],
        "variant": _branch_variant(selected["vietocr_text"]),
    }


def _owner_normalized(surface: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(surface)
    normalized = _SECTION_PREFIX.sub("", normalized)
    return re.sub(r"\s+tiep theo$", "", normalized)


def _owner_hits(page: Mapping[str, Any], *, top: int, bottom: int) -> list[dict[str, Any]]:
    aliases = {normalize_vietnamese_anchor_v1(alias) for alias in _OWNER_ALIASES}
    result = []
    lines = page["lines"]
    for start in range(len(lines)):
        for width in range(1, min(3, len(lines) - start) + 1):
            subset = lines[start : start + width]
            box = _union_bbox(lines, list(range(start, start + width)))
            if box[1] < top or box[1] >= bottom:
                continue
            surface = " ".join(line["vietocr_text"].strip() for line in subset).strip()
            if _owner_normalized(surface) not in aliases:
                continue
            result.append(
                {
                    "bbox": box,
                    "match_kind": "EXACT_ACCENTLESS_OWNER_ALIAS",
                    "page_sequence": page["page_sequence"],
                    "source_line_indices": list(range(start, start + width)),
                    "surface": surface,
                }
            )
            break
    return result


def _owner(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    branch: Mapping[str, Any],
    first_label_top: int,
) -> dict[str, Any] | None:
    post = _owner_hits(page, top=branch["bbox"][3], bottom=first_label_top)
    if post:
        selected = max(post, key=lambda item: (item["bbox"][1], item["source_line_indices"]))
        return {**selected, "mode": "POST_BRANCH_TABLE_PARENT"}
    same = _owner_hits(page, top=0, bottom=branch["bbox"][1])
    if same:
        selected = max(same, key=lambda item: (item["bbox"][1], item["source_line_indices"]))
        return {**selected, "mode": "SAME_PAGE_NEAREST_PRECEDING"}
    page_sequence = page["page_sequence"]
    if page_sequence <= 1:
        return None
    immediate_prior = pages[page_sequence - 2]
    if immediate_prior["page_sequence"] != page_sequence - 1:
        return None
    prior = _owner_hits(immediate_prior, top=0, bottom=10**12)
    if not prior:
        return None
    selected = max(
        prior,
        key=lambda item: (
            item["page_sequence"],
            item["bbox"][1],
            item["source_line_indices"],
        ),
    )
    return {**selected, "mode": "IMMEDIATE_PRECEDING_PAGE"}


def _date_surface(surface: str) -> str | None:
    matched = _DATE.search(surface)
    if matched is None:
        return None
    first, second, year = map(int, matched.groups())
    if 1 <= first <= 31 and 1 <= second <= 12:
        day, month = first, second
    elif 1 <= first <= 12 and 13 <= second <= 31:
        day, month = second, first
    else:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def _raw_date_evidence(header: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for line in header:
        semantic = line["vietocr_text"]
        source = line.get("source_text")
        if _DATE.search(semantic) is None and (
            type(source) is not str or _DATE.search(source) is None
        ):
            continue
        semantic_date = _date_surface(semantic)
        source_date = _date_surface(source) if type(source) is str else None
        result.append(
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "ppocrv6_surface": source,
                "selected_normalized_period": semantic_date or source_date,
                "selection_mode": (
                    "VIETOCR_EXACT_DATE"
                    if semantic_date is not None
                    else "BOUND_PPOCRV6_IMPOSSIBLE_DATE_CHALLENGER"
                    if source_date is not None
                    else "UNRESOLVED_DATE_SURFACES"
                ),
                "source_line_index": line["source_line_index"],
                "vietocr_transformer_surface": semantic,
            }
        )
    return result


def _relative_period_evidence(
    header: Sequence[Mapping[str, Any]], periods: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_index = {line["source_line_index"]: line for line in header}
    result = []
    for period in periods:
        indices = period.get("evidence_source_line_indices")
        if type(indices) is not list or len(indices) != 1 or type(indices[0]) is not int:
            return []
        line = by_index.get(indices[0])
        if line is None:
            return []
        normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
        year_end = normalized.startswith(("so cuoi nam", "so dau nam"))
        result.append(
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "ppocrv6_surface": line.get("source_text"),
                "selected_normalized_period": period.get("period"),
                "selection_mode": (
                    "VIETOCR_RELATIVE_YEAR_END_ROLE" if year_end else "VIETOCR_RELATIVE_PERIOD_ROLE"
                ),
                "source_line_index": line["source_line_index"],
                "vietocr_transformer_surface": line["vietocr_text"],
            }
        )
    return result


def _refined_relative_period_mode(
    header: Sequence[Mapping[str, Any]],
    periods: Sequence[Mapping[str, Any]],
    mode: str,
) -> tuple[str, list[dict[str, Any]]]:
    if mode != "LOCAL_RELATIVE_PERIOD_ROLES":
        return mode, []
    evidence = _relative_period_evidence(header, periods)
    normalized = [
        normalize_vietnamese_anchor_v1(item["vietocr_transformer_surface"]) for item in evidence
    ]
    prefixes = {
        "CURRENT_PERIOD_END": "so cuoi nam",
        "COMPARATIVE_PERIOD_START": "so dau nam",
    }
    year_end = len(evidence) == 2 and all(
        type(item["selected_normalized_period"]) is str
        and item["selected_normalized_period"] in prefixes
        and normalized[index].startswith(prefixes[item["selected_normalized_period"]])
        for index, item in enumerate(evidence)
    )
    return (
        "LOCAL_RELATIVE_YEAR_END_ROLES" if year_end else mode,
        evidence,
    )


def _period_axis(
    header: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    raw_evidence = _raw_date_evidence(header)
    try:
        periods, mode = extract_period_axis_v1(header)
    except AccountingTableAxesV1Error:
        periods, mode = [], "UNRESOLVED"
    if len(periods) == 2:
        refined_mode, relative_evidence = _refined_relative_period_mode(header, periods, mode)
        return periods, refined_mode, raw_evidence + relative_evidence

    # PP-OCR is already bound to the exact header box.  It may challenge an
    # impossible semantic date, but the raw texts are both retained and this
    # family layer does not grant the challenger general semantic authority.
    challenged = []
    replacement_count = 0
    mdy_count = 0
    for line in header:
        semantic_date = _date_surface(line["vietocr_text"])
        source = line.get("source_text")
        source_date = _date_surface(source) if type(source) is str else None
        selected = semantic_date or source_date
        copied = dict(line)
        if selected is not None:
            copied["vietocr_text"] = selected
            replacement_count += semantic_date is None and source_date is not None
            raw_match = _DATE.search(
                line["vietocr_text"] if semantic_date is not None else str(source)
            )
            if raw_match is not None and int(raw_match.group(1)) <= 12 < int(raw_match.group(2)):
                mdy_count += 1
        challenged.append(copied)
    try:
        periods, _fallback_mode = extract_period_axis_v1(challenged)
    except AccountingTableAxesV1Error:
        periods = []
    if len(periods) != 2:
        return [], "UNRESOLVED", raw_evidence
    if replacement_count:
        return periods, "BOUND_SOURCE_EXACT_DATE_CHALLENGER", raw_evidence
    if mdy_count:
        return periods, "LOCAL_UNAMBIGUOUS_MONTH_DAY_YEAR", raw_evidence
    return [], "UNRESOLVED", raw_evidence


def _is_boundary(surface: str) -> bool:
    normalized = normalize_vietnamese_anchor_v1(surface)
    return (
        normalized.startswith("phan tich ")
        or normalized.startswith("du phong rui ro cho vay")
        or normalized.startswith("theo ")
    )


def _labels(pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for match in region["child_matches"]:
        page = pages[match["page_sequence"] - 1]
        indices = _indices(match)
        result.append(
            {
                "bbox": _union_bbox(page["lines"], indices),
                "match_kind": match["match_kind"],
                "page_sequence": match["page_sequence"],
                "role": match["role"],
                "source_line_indices": indices,
                "surface": match["surface"],
            }
        )
    return sorted(result, key=lambda item: (item["page_sequence"], item["bbox"][1]))


def _inherited_unit(
    pages: Sequence[Mapping[str, Any]], *, page_sequence: int, before_top: int
) -> dict[str, Any] | None:
    hits = []
    for page in pages[:page_sequence]:
        for line in page["lines"]:
            if page["page_sequence"] == page_sequence and line["bbox"][1] >= before_top:
                continue
            if unit_kind_v1(line["vietocr_text"]) != "MONEY":
                continue
            normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
            if "don vi" in normalized or normalized in {
                "dong",
                "nghin dong",
                "trieu dong",
                "trieu vnd",
                "ty dong",
            }:
                hits.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["source_line_index"],
                        "surface": line["vietocr_text"],
                    }
                )
    return hits[-1] if hits else None


def _axis_and_body(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    branch: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    lines = page["lines"]
    first_top = min(label["bbox"][1] for label in labels)
    last_bottom = max(label["bbox"][3] for label in labels)
    scale = median_text_height_v1(lines)
    boundaries = [
        line["bbox"][1]
        for line in lines
        if line["bbox"][1] > last_bottom and _is_boundary(line["vietocr_text"])
    ]
    bottom = min(boundaries) if boundaries else int(round(last_bottom + scale * 15))
    header = [
        line
        for line in lines
        if line["bbox"][1] >= branch["bbox"][1] and line["bbox"][1] < first_top
    ]
    body = [
        line
        for line in lines
        if line["bbox"][3] >= first_top - scale * 1.2 and line["bbox"][1] < bottom
    ]
    units = [
        {
            "kind": kind,
            "source_line_index": line["source_line_index"],
            "surface": line["vietocr_text"],
            "x_center": center_x2_v1(line) / 2,
        }
        for line in header
        if (kind := unit_kind_v1(line["vietocr_text"])) is not None
    ]
    units.sort(key=lambda item: item["x_center"])
    page_width = max(line["bbox"][2] for line in lines) + 1
    minimum_ratio = max(
        0.05,
        min(
            0.45,
            (median(label["bbox"][2] for label in labels) + scale * 0.5) / page_width,
        ),
    )
    centers = infer_numeric_column_centers_v1(
        body,
        is_numeric=line_has_accounting_value_surface_v1,
        page_width=page_width,
        minimum_x_ratio=minimum_ratio,
        maximum_x_ratio=0.995,
    )
    if len(units) in {2, 4}:
        if len(centers) > len(units):
            selected = [
                min(
                    range(len(centers)),
                    key=lambda index: abs(centers[index] - unit["x_center"]),
                )
                for unit in units
            ]
            if len(set(selected)) == len(units):
                centers = [centers[index] for index in sorted(selected)]
        if len(centers) != len(units):
            centers = [unit["x_center"] for unit in units]
        lane_types = [unit["kind"] for unit in units]
        unit_scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [unit["source_line_index"] for unit in units],
            "surfaces": [unit["surface"] for unit in units],
        }
    elif len(centers) == 2:
        lane_types = ["MONEY", "MONEY"]
        inherited = _inherited_unit(
            pages, page_sequence=page["page_sequence"], before_top=first_top
        )
        unit_scope = (
            {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}
            if inherited is not None
            else {"mode": "UNRESOLVED"}
        )
    else:
        lane_types = []
        unit_scope = {"mode": "UNRESOLVED"}
    periods, period_mode, raw_date_evidence = _period_axis(header)
    return {
        "body": body,
        "bottom": bottom,
        "centers": centers,
        "header": header,
        "lane_types": lane_types,
        "minimum_ratio": minimum_ratio,
        "page_width": page_width,
        "period_mode": period_mode,
        "periods": periods,
        "raw_date_evidence": raw_date_evidence,
        "scale": scale,
        "unit_scope": unit_scope,
    }


def _cluster_vector(
    cluster: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
    centers: Sequence[float],
    *,
    primary_numeric_authority: bool,
) -> list[dict[str, Any]] | None:
    centers_x2 = [int(round(center * 2)) for center in centers]
    if len(centers_x2) < 2:
        return None
    gap = min(right - left for left, right in zip(centers_x2, centers_x2[1:], strict=False))
    tolerance = max(8, int(round(gap * 0.4)))
    by_lane: dict[int, Mapping[str, Any]] = {}
    for line in cluster:
        center = center_x2_v1(line)
        distances = [abs(center - expected) for expected in centers_x2]
        lane = min(range(len(distances)), key=distances.__getitem__)
        if distances[lane] > tolerance or lane in by_lane:
            continue
        by_lane[lane] = line
    if set(by_lane) != set(range(len(lane_types))):
        return None
    vector = extract_typed_value_vector_v1(
        [by_lane[index] for index in range(len(lane_types))],
        lane_types,
        primary_numeric_authority=primary_numeric_authority,
    )
    if vector is None:
        return None
    boxes = {line["source_line_index"]: line["bbox"] for line in cluster}
    for item in vector:
        item["bbox"] = canonical_clone_v1(boxes[item["source_line_index"]])
    return vector


def _numeric_rows(page: Mapping[str, Any], axes: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not axes["lane_types"]:
        return []
    body = axes["body"]
    clusters = cluster_numeric_rows_v1(
        body,
        is_numeric=line_has_accounting_value_surface_v1,
        start_index=-1,
        stop_index=max(line["source_line_index"] for line in body) + 1,
        page_width=axes["page_width"],
        minimum_x_ratio=axes["minimum_ratio"],
        maximum_x_ratio=0.995,
    )
    result = []
    for cluster in clusters:
        vector = _cluster_vector(
            cluster,
            axes["lane_types"],
            axes["centers"],
            primary_numeric_authority=page["primary_numeric_authority"],
        )
        if vector is None:
            continue
        result.append(
            {
                "center_y": float(
                    median((line["bbox"][1] + line["bbox"][3]) / 2 for line in cluster)
                ),
                "source_line_indices": sorted(item["source_line_index"] for item in vector),
                "vector": vector,
            }
        )
    return sorted(result, key=lambda item: item["center_y"])


def _role_rows(
    labels: Sequence[Mapping[str, Any]],
    numeric_rows: Sequence[Mapping[str, Any]],
    *,
    scale: float,
) -> list[dict[str, Any]] | None:
    first_top = labels[0]["bbox"][1]
    last_bottom = labels[-1]["bbox"][3]
    eligible = [
        row
        for row in numeric_rows
        if first_top - scale * 1.2 <= row["center_y"] <= last_bottom + scale * 0.2
    ]
    ranked = []
    for selected in combinations(eligible, len(_ROLES)):
        if list(selected) != sorted(selected, key=lambda item: item["center_y"]):
            continue
        score = sum(
            abs(row["center_y"] - (label["bbox"][1] + label["bbox"][3]) / 2)
            for row, label in zip(selected, labels, strict=True)
        )
        ranked.append((score, selected))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    if len(ranked) > 1 and abs(ranked[1][0] - ranked[0][0]) <= 1e-9:
        return None
    return [
        {
            "label": canonical_clone_v1(label),
            "role": label["role"],
            "value_row_center_y": row["center_y"],
            "values": canonical_clone_v1(row["vector"]),
        }
        for label, row in zip(labels, ranked[0][1], strict=True)
    ]


def _margin_surface(surface: str) -> bool:
    normalized = normalize_vietnamese_anchor_v1(surface)
    return "cho vay" in normalized and any(
        phrase in normalized for phrase in ("margin", "ung tru", "giao dich dau tu chung khoan")
    )


def _margin(
    page: Mapping[str, Any],
    role_rows: Sequence[Mapping[str, Any]],
    numeric_rows: Sequence[Mapping[str, Any]],
    axes: Mapping[str, Any],
) -> dict[str, Any] | None:
    last_label = role_rows[-1]["label"]["bbox"]
    hits = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= last_label[3] - axes["scale"]
        and line["bbox"][1] < axes["bottom"]
        and _margin_surface(line["vietocr_text"])
    ]
    if not hits:
        return None
    first_top = min(line["bbox"][1] for line in hits)
    candidate_rows = [
        row
        for row in numeric_rows
        if row["center_y"] > role_rows[-1]["value_row_center_y"] + axes["scale"] * 0.45
        and row["center_y"] >= first_top - axes["scale"] * 0.25
    ]
    if not candidate_rows:
        return None
    row = candidate_rows[0]
    return {
        "label_source_line_indices": [line["source_line_index"] for line in hits],
        "label_surface": " ".join(line["vietocr_text"].strip() for line in hits),
        "value_row_center_y": row["center_y"],
        "values": canonical_clone_v1(row["vector"]),
    }


def _vector_money(vector: Sequence[Mapping[str, Any]]) -> list[int] | None:
    return money_values_v1(vector)


def _vector_percent(vector: Sequence[Mapping[str, Any]]) -> list[Decimal] | None:
    return percentage_values_v1(vector)


def _label_value_vector(
    page: Mapping[str, Any],
    axes: Mapping[str, Any],
    *,
    label_boxes: Sequence[list[int]],
) -> list[dict[str, Any]]:
    """Bind every visible cell and retain an explicit hole for each missing lane."""

    assignments = assign_value_row_lanes_v1(
        axes["body"],
        label_boxes=label_boxes,
        is_numeric=line_has_accounting_value_surface_v1,
        page_width=axes["page_width"],
        minimum_x_ratio=axes["minimum_ratio"],
        maximum_x_ratio=0.995,
        resolved_column_centers=tuple(float(center) for center in axes["centers"]),
    )
    by_lane = {item["column_ordinal"]: item["line"] for item in assignments}
    result = []
    for lane_index, lane_type in enumerate(axes["lane_types"]):
        line = by_lane.get(lane_index)
        if line is None:
            result.append(
                {
                    "bbox": None,
                    "lane_index": lane_index,
                    "lane_type": lane_type,
                    "semantic_surface": None,
                    "source_authoritative": False,
                    "source_line_index": None,
                    "status": "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE",
                    "surface": None,
                    "x_center_x2": int(round(axes["centers"][lane_index] * 2)),
                }
            )
            continue
        vector = extract_typed_value_vector_v1(
            [line],
            [lane_type],
            primary_numeric_authority=page["primary_numeric_authority"],
        )
        if vector is None or len(vector) != 1:
            result.append(
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "lane_index": lane_index,
                    "lane_type": lane_type,
                    "semantic_surface": line["vietocr_text"],
                    "source_authoritative": False,
                    "source_line_index": line["source_line_index"],
                    "status": "VISIBLE_CELL_NOT_ONE_AUTHORITATIVE_TYPED_VALUE",
                    "surface": line.get("source_text"),
                    "x_center_x2": center_x2_v1(line),
                }
            )
            continue
        cell = vector[0]
        cell.update(
            {
                "bbox": canonical_clone_v1(line["bbox"]),
                "lane_index": lane_index,
                "status": "BOUND_PPOCRV6_VALUE_CELL",
            }
        )
        result.append(cell)
    return result


def _partial_money_values(vector: Sequence[Mapping[str, Any]]) -> list[int | None] | None:
    values: list[int | None] = []
    for expected_lane, item in enumerate(vector):
        if item.get("lane_index") != expected_lane or item.get("lane_type") != "MONEY":
            return None
        if item.get("status") == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE":
            values.append(None)
            continue
        surface = item.get("surface")
        if item.get("source_authoritative") is not True or type(surface) is not str:
            return None
        try:
            parsed = money_integer_v1(surface)
        except AccountingTableAxesV1Error:
            return None
        if parsed is None:
            return None
        values.append(parsed)
    return values


def _short_role_surface(surface: str) -> bool:
    normalized = normalize_vietnamese_anchor_v1(surface)
    aliases = {normalize_vietnamese_anchor_v1(alias) for alias in _ROLE_ALIASES["SHORT_TERM"]}
    return normalized in aliases


def _additional_population(
    page: Mapping[str, Any],
    axes: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
    numeric_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    last_bottom = labels[-1]["bbox"][3]
    parent_hits = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= last_bottom - axes["scale"]
        and line["bbox"][1] < axes["bottom"]
        and "nghiep vu phat hanh thu tin dung tra cham"
        in normalize_vietnamese_anchor_v1(line["vietocr_text"])
    ]
    if not parent_hits:
        return []
    parent = min(parent_hits, key=lambda line: (line["bbox"][1], line["source_line_index"]))
    continuation_hits = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= parent["bbox"][1]
        and line["bbox"][1] <= parent["bbox"][3] + axes["scale"] * 3.0
        and line["bbox"][1] < axes["bottom"]
        and "phat sinh truoc ngay" in normalize_vietnamese_anchor_v1(line["vietocr_text"])
    ]
    parent_lines = sorted(
        [parent, *continuation_hits],
        key=lambda line: (line["bbox"][1], line["source_line_index"]),
    )
    parent_bottom = max(line["bbox"][3] for line in parent_lines)
    child_hits = [
        line
        for line in page["lines"]
        if line["bbox"][1] >= parent_bottom - axes["scale"] * 0.2
        and line["bbox"][1] < axes["bottom"]
        and _short_role_surface(line["vietocr_text"])
    ]
    if not child_hits:
        return [
            {
                "classification": (
                    "SOURCE_ONLY_ADDITIVE_POPULATION_OUTSIDE_STRICT_THREE_BUCKET_CORE"
                ),
                "label_bbox": _union_bbox(
                    page["lines"], [line["source_line_index"] for line in parent_lines]
                ),
                "label_source_line_indices": [line["source_line_index"] for line in parent_lines],
                "label_surface": " ".join(line["vietocr_text"].strip() for line in parent_lines),
                "mapping_status": "SOURCE_ONLY_NOT_MAPPED_IN_MATURITY_SCHEMA",
                "status": "UNRESOLVED_REQUIRED_SHORT_TERM_BREAKDOWN_NOT_FOUND",
            }
        ]
    child = min(child_hits, key=lambda line: (line["bbox"][1], line["source_line_index"]))
    parent_boxes = [line["bbox"] for line in parent_lines]
    parent_vector = _label_value_vector(page, axes, label_boxes=parent_boxes)
    child_vector = _label_value_vector(page, axes, label_boxes=[child["bbox"]])
    grand_candidates = [
        row for row in numeric_rows if row["center_y"] > child["bbox"][3] + axes["scale"] * 0.1
    ]
    grand = grand_candidates[0] if grand_candidates else None
    return [
        {
            "classification": "SOURCE_ONLY_ADDITIVE_POPULATION_OUTSIDE_STRICT_THREE_BUCKET_CORE",
            "breakdown": {
                "label_bbox": canonical_clone_v1(child["bbox"]),
                "label_source_line_indices": [child["source_line_index"]],
                "label_surface": child["vietocr_text"],
                "role": "SHORT_TERM",
                "values": child_vector,
            },
            "grand_total": (
                {
                    "source_line_indices": canonical_clone_v1(grand["source_line_indices"]),
                    "value_row_center_y": grand["center_y"],
                    "values": canonical_clone_v1(grand["vector"]),
                }
                if grand is not None
                else None
            ),
            "label_bbox": _union_bbox(
                page["lines"], [line["source_line_index"] for line in parent_lines]
            ),
            "label_source_line_indices": [line["source_line_index"] for line in parent_lines],
            "label_surface": " ".join(line["vietocr_text"].strip() for line in parent_lines),
            "mapping_status": "SOURCE_ONLY_NOT_MAPPED_IN_MATURITY_SCHEMA",
            "status": "STRUCTURED_SOURCE_ONLY_ADDITIVE_POPULATION",
            "values": parent_vector,
        }
    ]


def _accounting(
    role_rows: Sequence[Mapping[str, Any]],
    numeric_rows: Sequence[Mapping[str, Any]],
    margin: Mapping[str, Any] | None,
    additional: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    reasons = []
    role_money = [_vector_money(row["values"]) for row in role_rows]
    if any(values is None for values in role_money):
        return {"status": "UNRESOLVED"}, ["ROLE_MONEY_VALUES_NOT_AUTHORITATIVE"]
    resolved_role_money = [values for values in role_money if values is not None]
    if len(resolved_role_money) != len(role_rows):
        return {"status": "UNRESOLVED"}, ["ROLE_MONEY_VALUES_NOT_AUTHORITATIVE"]
    core = [sum(values[lane] for values in resolved_role_money) for lane in range(2)]
    other = [
        row
        for row in numeric_rows
        if row["center_y"] not in {role["value_row_center_y"] for role in role_rows}
        and (margin is None or row["center_y"] != margin["value_row_center_y"])
    ]
    core_totals = [row for row in other if _vector_money(row["vector"]) == core]
    if len(core_totals) > 1:
        reasons.append("MULTIPLE_LANE_ALIGNED_CORE_TOTAL_ROWS")
    margin_money = _vector_money(margin["values"]) if margin is not None else None
    grand_target = (
        [core[index] + margin_money[index] for index in range(2)]
        if margin_money is not None
        else None
    )
    grand_totals = [
        row
        for row in other
        if grand_target is not None and _vector_money(row["vector"]) == grand_target
    ]
    if len(grand_totals) > 1:
        reasons.append("MULTIPLE_LANE_ALIGNED_GRAND_TOTAL_ROWS")
    additional_checks = []
    if margin is not None:
        if margin_money is None:
            reasons.append("MARGIN_MONEY_VALUES_NOT_AUTHORITATIVE")
        if len(grand_totals) != 1:
            reasons.append("CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED")
        variant = (
            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
            if core_totals
            else "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
        )
    else:
        if len(core_totals) != 1:
            reasons.append("THREE_BUCKET_CORE_TOTAL_NOT_CORROBORATED")
        variant = "CORE_TOTAL_ONLY"
        if additional:
            variant = "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL"
            if len(additional) != 1 or additional[0].get("status") != (
                "STRUCTURED_SOURCE_ONLY_ADDITIVE_POPULATION"
            ):
                reasons.append("ADDITIONAL_POPULATION_STRUCTURE_NOT_RESOLVED")
            else:
                population = additional[0]
                parent_values = _partial_money_values(population["values"])
                child_values = _partial_money_values(population["breakdown"]["values"])
                printed_grand = population.get("grand_total")
                grand_values = (
                    _vector_money(printed_grand["values"]) if type(printed_grand) is dict else None
                )
                if parent_values is None or child_values is None or grand_values is None:
                    reasons.append("ADDITIONAL_POPULATION_MONEY_AXIS_NOT_AUTHORITATIVE")
                else:
                    grand_target = []
                    grand_totals = []
                    for lane_index, (parent_value, child_value, grand_value) in enumerate(
                        zip(parent_values, child_values, grand_values, strict=True)
                    ):
                        if parent_value is None or child_value is None:
                            reasons.append("ADDITIONAL_POPULATION_VISIBLE_DASH_EVIDENCE_REQUIRED")
                            additional_checks.extend(
                                [
                                    {
                                        "equation": "ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN",
                                        "lane_index": lane_index,
                                        "left_value": parent_value,
                                        "right_value": child_value,
                                        "status": "REQUIRES_AUTHENTICATED_PIXEL_DASH_EVIDENCE",
                                    },
                                    {
                                        "addend_core": core[lane_index],
                                        "addend_source_only_population": parent_value,
                                        "equation": "CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND",
                                        "lane_index": lane_index,
                                        "printed_grand": grand_value,
                                        "status": "REQUIRES_AUTHENTICATED_PIXEL_DASH_EVIDENCE",
                                    },
                                ]
                            )
                            grand_target.append(None)
                            continue
                        equality_exact = parent_value == child_value
                        grand_exact = core[lane_index] + parent_value == grand_value
                        if not equality_exact:
                            reasons.append("ADDITIONAL_PARENT_SHORT_BREAKDOWN_EQUATION_FAILED")
                        if not grand_exact:
                            reasons.append("CORE_PLUS_ADDITIONAL_GRAND_TOTAL_EQUATION_FAILED")
                        additional_checks.extend(
                            [
                                {
                                    "equation": "ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN",
                                    "lane_index": lane_index,
                                    "left_value": parent_value,
                                    "right_value": child_value,
                                    "status": "EXACT" if equality_exact else "VETOED",
                                },
                                {
                                    "addend_core": core[lane_index],
                                    "addend_source_only_population": parent_value,
                                    "equation": "CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND",
                                    "lane_index": lane_index,
                                    "printed_grand": grand_value,
                                    "status": "EXACT" if grand_exact else "VETOED",
                                },
                            ]
                        )
                        grand_target.append(core[lane_index] + parent_value)
                    if all(item["status"] == "EXACT" for item in additional_checks):
                        grand_totals = [
                            {
                                "center_y": printed_grand["value_row_center_y"],
                                "source_line_indices": canonical_clone_v1(
                                    printed_grand["source_line_indices"]
                                ),
                                "vector": canonical_clone_v1(printed_grand["values"]),
                            }
                        ]

    percentage = [_vector_percent(row["values"]) for row in role_rows]
    percentage_totals = []
    if any(values for values in percentage):
        if any(values is None or len(values) != 2 for values in percentage):
            reasons.append("PERCENTAGE_CHILD_LANES_NOT_AUTHORITATIVE")
        else:
            resolved_percentage = [values for values in percentage if values is not None]
            if len(resolved_percentage) != len(role_rows):
                reasons.append("PERCENTAGE_CHILD_LANES_NOT_AUTHORITATIVE")
                resolved_percentage = []
            sums = [sum(values[lane] for values in resolved_percentage) for lane in range(2)]
            matching = []
            for total in core_totals:
                values = _vector_percent(total["vector"])
                if values is not None and values == [Decimal("100"), Decimal("100")]:
                    matching.append(total)
            if not matching or any(abs(value - Decimal("100")) > Decimal("0.05") for value in sums):
                reasons.append("PERCENTAGE_TOTAL_OR_ROUNDING_CLOSURE_FAILED")
            percentage_totals = matching
    return (
        {
            "core_money_values": core,
            "core_total_rows": canonical_clone_v1(core_totals),
            "grand_money_values": grand_target,
            "grand_total_rows": canonical_clone_v1(grand_totals),
            "additional_source_population_checks": canonical_clone_v1(additional_checks),
            "percentage_total_rows": canonical_clone_v1(percentage_totals),
            "status": "CORROBORATED" if not reasons else "VETOED",
            "variant": variant,
        },
        reasons,
    )


def _build_graph(pages: Sequence[Mapping[str, Any]], region: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    labels = _labels(pages, region)
    if len(labels) != len(_ROLES) or {label["role"] for label in labels} != set(_ROLES):
        reasons.append("THREE_REQUIRED_BUCKET_LABELS_NOT_RESOLVED")
    if len({label["page_sequence"] for label in labels}) != 1:
        reasons.append("CONTINUATION_NUMERIC_AXIS_REQUIRES_REPEAT_HEADER_RECONCILIATION")
        return {
            "accounting": {"status": "UNRESOLVED"},
            "additional_source_populations": [],
            "branch": None,
            "continuation_page_count": region["continuation_page_count"],
            "margin": None,
            "owner": None,
            "period_axis": {
                "mode": "UNRESOLVED",
                "periods": [],
                "raw_date_evidence": [],
            },
            "rows": [],
            "status": "UNRESOLVED",
            "unit_scope": {"mode": "UNRESOLVED"},
            "unresolved_reasons": sorted(set(reasons)),
        }
    page = pages[labels[0]["page_sequence"] - 1]
    branch = _branch(page, region, first_label_top=labels[0]["bbox"][1])
    if branch is None:
        reasons.append("MATURITY_BRANCH_NOT_RESOLVED")
        axes = None
    else:
        axes = _axis_and_body(pages, page, branch, labels)
    owner = _owner(pages, page, branch, labels[0]["bbox"][1]) if branch is not None else None
    if owner is None:
        reasons.append("CUSTOMER_LOAN_OWNER_NOT_RESOLVED")
    if axes is None:
        numeric_rows = []
        role_rows = None
    else:
        if len(axes["periods"]) != 2:
            reasons.append("TWO_PERIOD_AXIS_NOT_RESOLVED")
        if axes["lane_types"] not in (
            ["MONEY", "MONEY"],
            ["MONEY", "PERCENT", "MONEY", "PERCENT"],
        ):
            reasons.append("SUPPORTED_TYPED_LANE_AXIS_NOT_RESOLVED")
        if axes["unit_scope"]["mode"] == "UNRESOLVED":
            reasons.append("UNIT_SCOPE_NOT_RESOLVED")
        numeric_rows = _numeric_rows(page, axes)
        role_rows = _role_rows(labels, numeric_rows, scale=axes["scale"])
        if role_rows is None:
            reasons.append("GLOBAL_ORDERED_ROLE_VALUE_ROWS_NOT_RESOLVED")
    margin = (
        _margin(page, role_rows, numeric_rows, axes)
        if axes is not None and role_rows is not None
        else None
    )
    additional = (
        _additional_population(page, axes, labels, numeric_rows) if axes is not None else []
    )
    if role_rows is not None:
        accounting, accounting_reasons = _accounting(role_rows, numeric_rows, margin, additional)
        reasons.extend(accounting_reasons)
    else:
        accounting = {"status": "UNRESOLVED"}
    return {
        "accounting": accounting,
        "additional_source_populations": additional,
        "branch": branch,
        "continuation_page_count": region["continuation_page_count"],
        "margin": margin,
        "owner": owner,
        "period_axis": {
            "mode": axes["period_mode"] if axes is not None else "UNRESOLVED",
            "periods": canonical_clone_v1(axes["periods"]) if axes is not None else [],
            "raw_date_evidence": (
                canonical_clone_v1(axes["raw_date_evidence"]) if axes is not None else []
            ),
        },
        "rows": canonical_clone_v1(
            sorted(role_rows or [], key=lambda row: _ROLES.index(row["role"]))
        ),
        "status": "ACCEPTED_VARIANT_GRAPH" if not reasons else "UNRESOLVED",
        "unit_scope": (
            {
                **canonical_clone_v1(axes["unit_scope"]),
                "lane_types": canonical_clone_v1(axes["lane_types"]),
            }
            if axes is not None
            else {"mode": "UNRESOLVED"}
        ),
        "unresolved_reasons": sorted(set(reasons)),
    }


def _metrics(graphs: Sequence[Mapping[str, Any]], scan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "accepted_graph_count": sum(
            graph["status"] == "ACCEPTED_VARIANT_GRAPH" for graph in graphs
        ),
        "additional_source_population_count": sum(
            len(graph["additional_source_populations"]) for graph in graphs
        ),
        "complete_region_count": scan["metrics"]["complete_region_count"],
        "mapped_role_candidate_count": sum(len(graph["rows"]) for graph in graphs),
        "optional_margin_candidate_count": sum(graph["margin"] is not None for graph in graphs),
        "percentage_child_cell_count": sum(
            item["lane_type"] == "PERCENT"
            for graph in graphs
            for row in graph["rows"]
            for item in row["values"]
        ),
        "source_total_percentage_corroboration_cell_count": sum(
            len(total["vector"]) // 2
            for graph in graphs
            for total in graph.get("accounting", {}).get("percentage_total_rows", [])
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("maturity V2 result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _SAFETY
        or type(value["graphs"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["region_scan"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("maturity V2 result contract drifted")
    material = {key: value[key] for key in sorted(_RESULT_FIELDS - {"result_id"})}
    if value["result_id"] != "lmvgv2:result:" + canonical_json_sha256_v1(material):
        raise _error("maturity V2 result identity drifted")
    if value["status"] not in {"ACCEPTED_VARIANT_GRAPH", "UNRESOLVED"}:
        raise _error("maturity V2 status drifted")
    return canonical_clone_v1(value)


def _validated_topology_scan(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("maturity V2 topology scan is not one object")
    material = canonical_clone_v1(value)
    scan_id = material.pop("scan_id", None)
    if (
        material.get("format_version") != "ACCOUNTING_FAMILY_TOPOLOGY_SCAN_V1"
        or material.get("family_id") != FAMILY_ID
        or scan_id != "aftv1:scan:" + canonical_json_sha256_v1(material)
        or type(material.get("regions")) is not list
        or type(material.get("near_regions")) is not list
    ):
        raise _error("maturity V2 topology scan identity drifted")
    return canonical_clone_v1(value)


def _build_result(pages: Sequence[Mapping[str, Any]], scan: Mapping[str, Any]) -> dict[str, Any]:
    regions = scan["regions"]
    graphs = [_build_graph(pages, regions[0])] if len(regions) == 1 else []
    uniqueness = {
        "complete_region_count": len(regions),
        "minimal_role_combination_proved": (
            len(regions) == 1
            and regions[0]["minimal_unique_anchor"]["combination_size"] == 2
            and regions[0]["minimal_unique_anchor"]["pair_before_triple_search"] is True
        ),
    }
    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if len(graphs) == 1
        and graphs[0]["status"] == "ACCEPTED_VARIANT_GRAPH"
        and uniqueness["minimal_role_combination_proved"]
        else "UNRESOLVED"
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": _metrics(graphs, scan),
        "region_scan": canonical_clone_v1(scan),
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "uniqueness": uniqueness,
    }
    return _validate(
        {**material, "result_id": "lmvgv2:result:" + canonical_json_sha256_v1(material)}
    )


def build_loan_maturity_variant_graph_from_topology_scan_v2(
    document_pages: Sequence[Mapping[str, Any]], topology_scan: Mapping[str, Any]
) -> dict[str, Any]:
    """Solve local geometry/accounting from a content-authenticated shortlist."""

    pages = _pages(document_pages)
    scan = _validated_topology_scan(topology_scan)
    return _build_result(pages, scan)


def build_loan_maturity_variant_graph_document_v2(
    document_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one complete-document maturity graph proposal."""

    pages = _pages(document_pages)
    scan = build_accounting_family_topology_scan_v1(
        _topology_pages(pages), LOAN_MATURITY_TOPOLOGY_SPEC_V2
    )
    return _build_result(pages, scan)


def validate_loan_maturity_variant_graph_document_v2(value: Any) -> dict[str, Any]:
    """Validate one persisted/projection graph without rebuilding it."""

    return _validate(value)


def validate_loan_maturity_variant_graph_replay_v2(
    value: Any, document_pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rebuild one graph and require exact typed replay."""

    persisted = _validate(value)
    rebuilt = build_loan_maturity_variant_graph_document_v2(document_pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("maturity V2 graph does not replay exactly")
    return canonical_clone_v1(rebuilt)
