"""Bank-blind variant graph for customer-loan type tables.

The table immediately below ``Cho vay khach hang`` is commonly represented in
the reporting schema as ``Phan tich theo loai hinh cho vay`` even when that
intermediate title is not printed in the PDF.  This matcher therefore treats
the owner followed by period/unit axes and a sufficiently rich set of typed
loan rows as the structural branch.  It never uses a bank, filename, note
number, or page number.

Rows may be reordered, wrapped, absent, or rendered with missing dash glyphs.
The common graph also supports money/percent companion lanes and the generic
``core subtotal -> margin/advance -> grand total`` presentation.  Fresh
VietOCR text is anchor evidence only.  Numeric and mapping authority require a
separate source-pixel review.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from functools import lru_cache
from typing import Any

from rapidfuzz.fuzz import ratio

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    AccountingTableAxesV1Error,
    center_x2_v1,
    extract_period_axis_v1,
    is_number_like_v1,
    money_integer_v1,
    unit_kind_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
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
    "LoanTypeVariantGraphV1Error",
    "build_loan_type_variant_graph_document_v1",
    "validate_loan_type_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_TYPE_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_TYPE_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_LOAN_TYPE_STRUCTURE_"
    "GEOMETRY_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_PROPOSAL_CORROBORATION_ONLY_"
    "TEXT_IS_ANCHOR_NO_SOURCE_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_OWNER_ALIASES = (
    "Cho vay khách hàng",
    "Các khoản cho vay khách hàng",
)
_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "DOMESTIC_ORGANIZATIONS_INDIVIDUALS": (
        "Cho vay các tổ chức kinh tế, cá nhân trong nước",
        "Cho vay các tổ chức kinh tế và cá nhân trong nước",
        "Cho vay các TCKT, cá nhân trong nước",
        "Cho vay các tổ chức kinh tế, cá nhân",
        "Cho vay các tổ chức kinh tế và cá nhân",
    ),
    "FINANCIAL_LEASE": ("Cho thuê tài chính",),
    "GOVERNMENT_DIRECTED_OR_FUNDED": (
        "Cho vay từ nguồn vốn từ Chính phủ, các tổ chức quốc tế khác",
        "Cho vay theo chỉ định của Chính phủ",
    ),
    "FOREIGN_ORGANIZATIONS_INDIVIDUALS": (
        "Cho vay cá nhân và tổ chức nước ngoài",
        "Cho vay đối với các tổ chức, cá nhân nước ngoài",
        "Cho vay các TCKT, cá nhân nước ngoài",
    ),
    "DISCOUNT_INSTRUMENTS": (
        "Cho vay chiết khấu thương phiếu và các giấy tờ có giá",
        "Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá",
    ),
    "PAYMENTS_ON_BEHALF": ("Các khoản trả thay khách hàng",),
    "FROZEN_OR_PENDING_LOANS": (
        "Nợ cho vay được khoanh và nợ chờ xử lý",
        "Nợ cho vay khoanh và nợ chờ xử lý",
    ),
    "ENTRUSTED_OR_SPONSORED_CAPITAL": ("Cho vay bằng vốn tài trợ, ủy thác đầu tư",),
    "OTHER_LOANS": ("Cho vay khác",),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "Cho vay giao dịch ký quỹ, ứng trước cho khách hàng",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng",
    ),
    # Deliberately not mapped to OTHER_LOANS.  It is retained as a source-only
    # row until schema semantics establish that the broader phrase is eligible.
    "UNMAPPED_OTHER_CREDIT": ("Cấp tín dụng khác",),
}
_EXTENDED_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "FINANCIAL_LEASE": ("Các khoản phải thu từ cho thuê tài chính",),
    "FOREIGN_ORGANIZATIONS_INDIVIDUALS": ("Cho vay các tổ chức, cá nhân nước ngoài",),
    "PAYMENTS_ON_BEHALF": ("Các khoản phải trả thay khách hàng",),
    "OTHER_LOANS": (
        "Cho vay trong nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản trả ngay",
        "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
    ),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
        "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch đầu tư chứng khoán",
    ),
}
_SCHEMA_ELIGIBLE_ROLES = tuple(role for role in _ROLE_ALIASES if role != "UNMAPPED_OTHER_CREDIT")
_MIN_SCHEMA_ROLE_COUNT = 2
_MAX_OWNER_TABLE_LINE_SPAN = 80
_MAX_LABEL_WIDTH = 3
_BOUNDARY_PREFIXES = (
    "phan tich chat luong",
    "phan tich du no cho vay theo chat luong",
    "phan tich du no theo thoi",
    "phan tich du no cho vay theo thoi",
    "phan tich du no cho vay theo nganh",
    "phan tich du no theo nganh",
    "phan tich du no cho vay theo doi tuong",
    "phan tich du no theo doi tuong",
    "du phong rui ro cho vay khach hang",
)
_COMPACT_SIBLING_BOUNDARY_PREFIXES = (
    "phan tich du no theo chat luong",
    "theo doi tuong khach hang",
    "theo chat luong no cho vay",
    "theo chat luong du no cho vay",
    "theo ky han",
)
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "blank_or_missing_companion_cells_imputed_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "legacy_ocr_used_for_semantic_anchors": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "optional_rows_required_to_keep_fixed_order": False,
    "percentage_companion_lanes_preserved": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "qwen_or_gemma_used_for_semantic_anchors": False,
    "text_similarity_alone_can_accept": False,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "graphs",
    "metrics",
    "near_regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_SECTION = re.compile(r"^\d{1,3}(?:\.\d{1,2})*\.?$")


class LoanTypeVariantGraphV1Error(ValueError):
    """The complete-document semantic line axis or loan-type graph drifted."""


def _error(message: str) -> LoanTypeVariantGraphV1Error:
    return LoanTypeVariantGraphV1Error(message)


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
        raise _error("loan-type scan requires one non-empty complete PDF page sequence")
    pages: list[dict[str, Any]] = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error(f"loan-type page {page_offset} fields drifted")
        if type(raw_page["page_sequence"]) is not int or raw_page["page_sequence"] <= 0:
            raise _error("loan-type page sequence drifted")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("loan-type numeric authority flag drifted")
        if type(raw_page["lines"]) is not list:
            raise _error("loan-type line axis drifted")
        lines: list[dict[str, Any]] = []
        for line_offset, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-type semantic line fields drifted")
            if (
                type(raw_line["source_line_index"]) is not int
                or raw_line["source_line_index"] != line_offset
                or type(raw_line["vietocr_text"]) is not str
                or (
                    raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str
                )
            ):
                raise _error("loan-type semantic line identity/text drifted")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], "loan-type semantic line"),
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
        raise _error("loan-type document pages must be unique and ordered")
    return pages


def _joined(lines: Sequence[Mapping[str, Any]], start: int, stop: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start:stop]).strip()


def _owner_surface(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value)
    normalized = re.sub(r"^(?:\d+\s+)+", "", normalized)
    normalized = re.sub(r"\s+tiep theo$", "", normalized)
    return normalized


def _owner_window(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any] | None:
    first_normalized = _owner_surface(lines[start]["vietocr_text"])
    if not (
        first_normalized.startswith("cho vay") or first_normalized.startswith("cac khoan cho vay")
    ):
        return None
    aliases = [normalize_vietnamese_anchor_v1(alias) for alias in _OWNER_ALIASES]
    for width in range(1, min(_MAX_LABEL_WIDTH, len(lines) - start) + 1):
        surface = _joined(lines, start, start + width)
        normalized = _owner_surface(surface)
        if normalized in aliases:
            return {
                "match_kind": "EXACT_ACCENTLESS_ALIAS",
                "source_line_indices": list(range(start, start + width)),
                "surface": surface,
            }
        if match_vietnamese_anchor_alias_v1(normalized, aliases) is not None:
            return {
                "match_kind": "ONE_EDIT_ALIAS_IN_COMPLETE_TOPOLOGY",
                "source_line_indices": list(range(start, start + width)),
                "surface": surface,
            }
    return None


def _is_boundary(text: str, *, enable_extended_owner_table_variants: bool) -> bool:
    normalized = normalize_vietnamese_anchor_v1(text)
    normalized = re.sub(r"^\d{1,3}(?:\s+\d{1,2})*\s+", "", normalized)
    prefixes = _BOUNDARY_PREFIXES + (
        _COMPACT_SIBLING_BOUNDARY_PREFIXES if enable_extended_owner_table_variants else ()
    )
    return any(normalized.startswith(prefix) for prefix in prefixes)


def _table_stop(
    lines: Sequence[Mapping[str, Any]],
    owner_stop: int,
    *,
    enable_extended_owner_table_variants: bool,
) -> int:
    hard_stop = min(len(lines), owner_stop + _MAX_OWNER_TABLE_LINE_SPAN)
    for index in range(owner_stop, hard_stop):
        if _is_boundary(
            lines[index]["vietocr_text"],
            enable_extended_owner_table_variants=enable_extended_owner_table_variants,
        ):
            return index
    return hard_stop


def _union_bbox(lines: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> list[int]:
    boxes = [lines[index]["bbox"] for index in indices]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _line_is_number_like(line: Mapping[str, Any]) -> bool:
    if is_number_like_v1(line["vietocr_text"]):
        return True
    challenger = line.get("source_text")
    return type(challenger) is str and is_number_like_v1(challenger)


@lru_cache(maxsize=4096)
def _role_anchor_match(surface: str, aliases: tuple[str, ...]) -> str | None:
    """Admit bounded OCR spelling drift only as a structural anchor.

    VietOCR occasionally adds or drops several base characters in a long row
    label even after accent removal.  A single-edit matcher is then too
    brittle, while unconstrained fuzzy matching would let text decide the
    mapping.  The high threshold below is restricted to long labels; callers
    still require the owner, period/unit axes, value geometry, a final total,
    uniqueness, and a separate numeric/mapping replay.
    """

    exact = match_vietnamese_anchor_alias_v1(surface, aliases)
    if exact is not None:
        return exact
    normalized = normalize_vietnamese_anchor_v1(surface)
    normalized_aliases = tuple(normalize_vietnamese_anchor_v1(alias) for alias in aliases)
    if len(normalized) >= 24 and any(
        alias.startswith(normalized + " ") for alias in normalized_aliases
    ):
        return "LONG_PREFIX_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY"
    scores = [ratio(normalized, alias) for alias in normalized_aliases if len(alias) >= 20]
    if scores and max(scores) >= 90.0:
        return "HIGH_SIMILARITY_ACCENTLESS_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY"
    return None


def _label_candidates(
    lines: Sequence[Mapping[str, Any]],
    start: int,
    stop: int,
    *,
    enable_extended_owner_table_variants: bool,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    occupied: set[int] = set()
    visual_text_indices = [
        index
        for index in range(start, stop)
        if not _line_is_number_like(lines[index])
        and (not enable_extended_owner_table_variants or lines[index]["vietocr_text"].strip())
        and re.fullmatch(r"[ivx]+", normalize_vietnamese_anchor_v1(lines[index]["vietocr_text"]))
        is None
    ]
    visual_text_indices.sort(
        key=lambda index: (
            lines[index]["bbox"][1],
            lines[index]["bbox"][0],
            lines[index]["source_line_index"],
        )
    )
    for visual_position, line_index in enumerate(visual_text_indices):
        if line_index in occupied:
            continue
        text_indices: list[int] = []
        selected: tuple[list[int], str, str, str] | None = None
        first_box = lines[line_index]["bbox"]
        for candidate_index in visual_text_indices[
            visual_position : visual_position + _MAX_LABEL_WIDTH
        ]:
            candidate_box = lines[candidate_index]["bbox"]
            if text_indices:
                previous_box = lines[text_indices[-1]]["bbox"]
                previous_height = previous_box[3] - previous_box[1]
                if candidate_box[1] - previous_box[3] > max(12, previous_height):
                    break
            if abs(candidate_box[0] - first_box[0]) > max(300, first_box[2] - first_box[0]):
                # Provider order can interleave a stamp fragment or other
                # far-right token between two visually wrapped label lines.
                # Ignore the off-column token; the vertical-gap guard still
                # prevents joining a genuinely later row.
                continue
            text_indices.append(candidate_index)
            indices = list(text_indices)
            surface = " ".join(lines[index]["vietocr_text"].strip() for index in indices).strip()
            match_surface = (
                re.sub(r"\s*\([ivx]+\)\s*$", "", surface, flags=re.IGNORECASE)
                if enable_extended_owner_table_variants
                else surface
            )
            normalized_surface = normalize_vietnamese_anchor_v1(match_surface)
            exact_alias_can_extend = False
            for role, base_aliases in _ROLE_ALIASES.items():
                aliases = base_aliases + (
                    _EXTENDED_ROLE_ALIASES.get(role, ())
                    if enable_extended_owner_table_variants
                    else ()
                )
                kind = _role_anchor_match(match_surface, aliases)
                if kind is not None:
                    proposal = (indices, role, kind, surface)
                    if selected is None or kind == "EXACT_ACCENTLESS_ALIAS":
                        selected = proposal
                    if kind == "EXACT_ACCENTLESS_ALIAS" and any(
                        normalize_vietnamese_anchor_v1(alias).startswith(normalized_surface + " ")
                        for alias in aliases
                    ):
                        exact_alias_can_extend = True
            if (
                selected is not None
                and selected[2]
                not in {
                    "HIGH_SIMILARITY_ACCENTLESS_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY",
                    "LONG_PREFIX_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY",
                }
                and not exact_alias_can_extend
            ):
                break
        if selected is None:
            continue
        indices, role, kind, surface = selected
        occupied.update(indices)
        box = _union_bbox(lines, indices)
        matches.append(
            {
                "bbox": box,
                "match_kind": kind,
                "role": role,
                "source_line_indices": indices,
                "surface": surface,
                "y_center_x2": box[1] + box[3],
                # A wrapped accounting label can place its numeric cells on
                # the terminal text baseline rather than the centre of the
                # union box.  Retain every visible label-line baseline as an
                # alignment candidate; the monotonic global assignment below
                # still decides the row and prevents an isolated nearest-line
                # match from crossing a sibling.
                "y_center_candidates_x2": sorted(
                    {
                        box[1] + box[3],
                        *(lines[index]["bbox"][1] + lines[index]["bbox"][3] for index in indices),
                    }
                ),
            }
        )
    return sorted(matches, key=lambda item: (item["y_center_x2"], item["source_line_indices"][0]))


def _inherited_unit(
    pages: Sequence[Mapping[str, Any]], target_page: int, before_line: int
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        if page["page_sequence"] > target_page:
            break
        for line in page["lines"]:
            if page["page_sequence"] == target_page and line["source_line_index"] >= before_line:
                continue
            normalized = normalize_vietnamese_anchor_v1(line["vietocr_text"])
            if "don vi" in normalized and unit_kind_v1(line["vietocr_text"]) == "MONEY":
                candidates.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "source_line_index": line["source_line_index"],
                        "surface": line["vietocr_text"],
                    }
                )
    return candidates[-1] if candidates else None


def _axes(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    owner_stop: int,
    owner: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
    *,
    enable_extended_owner_table_variants: bool,
) -> tuple[list[dict[str, Any]], str, list[str], list[int], dict[str, Any], list[str]]:
    lines = page["lines"]
    owner_indices = set(owner["source_line_indices"])
    owner_top = min(lines[index]["bbox"][1] for index in owner_indices)
    first_label_top = min(label["bbox"][1] for label in labels)
    source_first_label = min(label["source_line_indices"][0] for label in labels)
    header_by_geometry = [
        line
        for line in lines
        if line["source_line_index"] not in owner_indices
        and line["bbox"][1] >= owner_top
        and line["bbox"][3] <= first_label_top
    ]
    header_by_index = lines[owner_stop:source_first_label]
    header = list(
        {
            line["source_line_index"]: line for line in (*header_by_index, *header_by_geometry)
        }.values()
    )
    period_header = []
    for line in header:
        challenger = line.get("source_text")
        period_header.append(
            {
                **line,
                **(
                    {"numeric_score": 1.0, "numeric_text": challenger}
                    if page["primary_numeric_authority"] and type(challenger) is str
                    else {}
                ),
            }
        )
    reasons: list[str] = []
    try:
        periods, period_mode = extract_period_axis_v1(period_header)
    except AccountingTableAxesV1Error:
        periods, period_mode = [], "UNRESOLVED"
    if enable_extended_owner_table_variants and period_mode == "LOCAL_RELATIVE_PERIOD_ROLES":
        period_mode = "LOCAL_RELATIVE_YEAR_END_PERIOD_ROLES"
    if len(periods) != 2 and enable_extended_owner_table_variants:
        relative_by_surface = {
            "so cuoi nam": "CURRENT_PERIOD_END",
            "so dau nam": "COMPARATIVE_PERIOD_START",
        }
        relative = [
            {
                "evidence_source_line_indices": [line["source_line_index"]],
                "period": role,
                "x_center_x2": center_x2_v1(line),
            }
            for line in header
            if (
                role := relative_by_surface.get(
                    normalize_vietnamese_anchor_v1(line["vietocr_text"])
                )
            )
        ]
        if len(relative) == 2 and {item["period"] for item in relative} == set(
            relative_by_surface.values()
        ):
            periods = sorted(relative, key=lambda item: item["x_center_x2"])
            period_mode = "LOCAL_RELATIVE_YEAR_END_PERIOD_ROLES"
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
    if len(local_units) == 4 and [item["kind"] for item in local_units] == [
        "MONEY",
        "PERCENT",
        "MONEY",
        "PERCENT",
    ]:
        lane_types = [item["kind"] for item in local_units]
        lane_centers = [item["x_center_x2"] for item in local_units]
        unit_scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [item["source_line_index"] for item in local_units],
            "surfaces": [item["surface"] for item in local_units],
        }
    elif len(local_units) == 2 and all(item["kind"] == "MONEY" for item in local_units):
        lane_types = ["MONEY", "MONEY"]
        lane_centers = [item["x_center_x2"] for item in local_units]
        unit_scope = {
            "mode": "LOCAL_PER_LANE",
            "source_line_indices": [item["source_line_index"] for item in local_units],
            "surfaces": [item["surface"] for item in local_units],
        }
    elif len(local_units) == 1 and local_units[0]["kind"] == "MONEY" and len(periods) == 2:
        lane_types = ["MONEY", "MONEY"]
        lane_centers = [item["x_center_x2"] for item in periods]
        unit_scope = {
            "mode": "LOCAL_SHARED_MONEY_UNIT",
            "source_line_indices": [local_units[0]["source_line_index"]],
            "surfaces": [local_units[0]["surface"]],
        }
    elif not local_units and len(periods) == 2:
        inherited = _inherited_unit(
            pages, page["page_sequence"], page["lines"][owner_stop - 1]["source_line_index"]
        )
        lane_types = ["MONEY", "MONEY"]
        lane_centers = [item["x_center_x2"] for item in periods]
        if inherited is None:
            unit_scope = {"mode": "UNRESOLVED"}
            reasons.append("UNIT_SCOPE_NOT_RESOLVED")
        else:
            unit_scope = {"mode": "INHERITED_DOCUMENT_MONEY_UNIT", **inherited}
    else:
        lane_types = []
        lane_centers = []
        unit_scope = {"mode": "UNRESOLVED_LOCAL_UNIT_LAYOUT"}
        reasons.append("SUPPORTED_TYPED_LANE_AXIS_NOT_RESOLVED")
    return periods, period_mode, lane_types, lane_centers, unit_scope, reasons


def _nearest_lane(x_center_x2: int, lane_centers: Sequence[int]) -> int | None:
    if not lane_centers:
        return None
    nearest = min(
        range(len(lane_centers)), key=lambda index: abs(lane_centers[index] - x_center_x2)
    )
    if len(lane_centers) == 1:
        return nearest
    gaps = [abs(right - left) for left, right in zip(lane_centers, lane_centers[1:], strict=False)]
    tolerance = max(80, min(gaps) * 2 // 5)
    return nearest if abs(lane_centers[nearest] - x_center_x2) <= tolerance else None


def _numeric_row_clusters(
    lines: Sequence[Mapping[str, Any]],
    first_line: int,
    stop: int,
    lane_centers: Sequence[int],
) -> list[dict[str, Any]]:
    candidates = []
    for line in lines[first_line:stop]:
        if not _line_is_number_like(line):
            continue
        lane = _nearest_lane(center_x2_v1(line), lane_centers)
        if lane is None:
            continue
        candidates.append(
            {
                "center_x2": line["bbox"][1] + line["bbox"][3],
                "lane": lane,
                "line": line,
            }
        )
    candidates.sort(
        key=lambda item: (
            item["center_x2"],
            item["lane"],
            item["line"]["source_line_index"],
        )
    )
    heights = sorted(item["line"]["bbox"][3] - item["line"]["bbox"][1] for item in candidates)
    median_height = heights[len(heights) // 2] if heights else 20
    tolerance = max(12, median_height * 3 // 4)
    clusters: list[dict[str, Any]] = []
    for item in candidates:
        if (
            not clusters
            or item["lane"] in clusters[-1]["by_lane"]
            or abs(item["center_x2"] - clusters[-1]["center_x2"]) > tolerance
        ):
            clusters.append(
                {
                    "by_lane": {item["lane"]: item["line"]},
                    "center_values": [item["center_x2"]],
                    "center_x2": item["center_x2"],
                }
            )
            continue
        cluster = clusters[-1]
        cluster["by_lane"][item["lane"]] = item["line"]
        cluster["center_values"].append(item["center_x2"])
        ordered = sorted(cluster["center_values"])
        cluster["center_x2"] = ordered[len(ordered) // 2]
    return clusters


def _align_labels_to_numeric_clusters(
    labels: Sequence[Mapping[str, Any]], clusters: Sequence[Mapping[str, Any]]
) -> dict[int, int]:
    """Find a minimum-cost monotonic label/row alignment.

    Columns in a PDF table can be vertically staggered and provider line order
    can differ from pixel order.  Aligning complete cross-lane row clusters is
    more stable than independently choosing the nearest number in each lane.
    Optional/dash rows may skip a label; unmodelled visible rows or subtotals
    may skip a numeric cluster.
    """

    skip_cost = 48
    maximum_match_distance = 80
    label_count = len(labels)
    cluster_count = len(clusters)
    costs = [[10**9] * (cluster_count + 1) for _ in range(label_count + 1)]
    previous: list[list[tuple[int, int, str] | None]] = [
        [None] * (cluster_count + 1) for _ in range(label_count + 1)
    ]
    costs[0][0] = 0
    for label_index in range(label_count + 1):
        for cluster_index in range(cluster_count + 1):
            if label_index == 0 and cluster_index == 0:
                continue
            options: list[tuple[int, int, int, str]] = []
            if label_index:
                options.append(
                    (
                        costs[label_index - 1][cluster_index] + skip_cost,
                        2,
                        label_index - 1,
                        "SKIP_LABEL",
                    )
                )
            if cluster_index:
                options.append(
                    (
                        costs[label_index][cluster_index - 1] + skip_cost,
                        1,
                        label_index,
                        "SKIP_CLUSTER",
                    )
                )
            if label_index and cluster_index:
                candidates = labels[label_index - 1].get(
                    "y_center_candidates_x2",
                    [labels[label_index - 1]["y_center_x2"]],
                )
                distance = min(
                    abs(center - clusters[cluster_index - 1]["center_x2"]) for center in candidates
                )
                if distance <= maximum_match_distance:
                    options.append(
                        (
                            costs[label_index - 1][cluster_index - 1] + distance,
                            0,
                            label_index - 1,
                            "MATCH",
                        )
                    )
            cost, _priority, prior_label, operation = min(options)
            costs[label_index][cluster_index] = cost
            prior_cluster = (
                cluster_index - 1 if operation in {"SKIP_CLUSTER", "MATCH"} else cluster_index
            )
            previous[label_index][cluster_index] = (prior_label, prior_cluster, operation)
    matches: dict[int, int] = {}
    label_index = label_count
    cluster_index = cluster_count
    while label_index or cluster_index:
        step = previous[label_index][cluster_index]
        if step is None:
            raise _error("loan-type row-cluster alignment is incomplete")
        prior_label, prior_cluster, operation = step
        if operation == "MATCH":
            matches[label_index - 1] = cluster_index - 1
        label_index, cluster_index = prior_label, prior_cluster
    return matches


def _value_record(line: Mapping[str, Any], lane_index: int, lane_type: str) -> dict[str, Any]:
    return {
        "lane_index": lane_index,
        "lane_type": lane_type,
        "semantic_surface": line["vietocr_text"],
        "source_line_index": line["source_line_index"],
        "status": "SEMANTIC_PROPOSAL_ONLY",
        "x_center_x2": center_x2_v1(line),
    }


def _rows_and_totals(
    page: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
    first_line: int,
    stop: int,
    lane_types: Sequence[str],
    lane_centers: Sequence[int],
) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]], list[str]]:
    lines = page["lines"]
    reasons: list[str] = []
    rows: list[dict[str, Any]] = []
    clusters = _numeric_row_clusters(lines, first_line, stop, lane_centers)
    aligned = _align_labels_to_numeric_clusters(labels, clusters)
    assigned_clusters: set[int] = set()
    for label_index, label in enumerate(labels):
        cluster_index = aligned.get(label_index)
        by_lane = {} if cluster_index is None else clusters[cluster_index]["by_lane"]
        if cluster_index is not None:
            assigned_clusters.add(cluster_index)
        values: list[dict[str, Any]] = []
        for lane_index, lane_type in enumerate(lane_types):
            line = by_lane.get(lane_index)
            if line is None:
                values.append(
                    {
                        "lane_index": lane_index,
                        "lane_type": lane_type,
                        "semantic_surface": None,
                        "source_line_index": None,
                        "status": "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
                        "x_center_x2": lane_centers[lane_index],
                    }
                )
            else:
                values.append(_value_record(line, lane_index, lane_type))
        rows.append(
            {
                "label": {
                    key: canonical_clone_v1(label[key])
                    for key in ("bbox", "match_kind", "source_line_indices", "surface")
                },
                "role": label["role"],
                "values": values,
            }
        )

    totals: list[list[dict[str, Any]]] = []
    for cluster_index, cluster in enumerate(clusters):
        if cluster_index in assigned_clusters:
            continue
        by_lane = cluster["by_lane"]
        money_lanes = [index for index, kind in enumerate(lane_types) if kind == "MONEY"]
        if not money_lanes or any(index not in by_lane for index in money_lanes):
            continue
        totals.append(
            [_value_record(by_lane[index], index, lane_types[index]) for index in sorted(by_lane)]
        )
    if not totals:
        reasons.append("FINAL_TOTAL_NOT_RESOLVED")
    return rows, totals, sorted(set(reasons))


def _decimal_percentage(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value.strip().replace("%", "").replace(",", "."))
    except Exception:  # Decimal has several string failure subclasses.
        return None
    return parsed if parsed.is_finite() else None


def _semantic_accounting(
    rows: Sequence[Mapping[str, Any]], totals: Sequence[Sequence[Mapping[str, Any]]]
) -> list[dict[str, Any]]:
    if not totals:
        return []
    final = {item["lane_index"]: item for item in totals[-1]}
    checks: list[dict[str, Any]] = []
    lane_types = [item["lane_type"] for item in rows[0]["values"]] if rows else []
    for lane_index, lane_type in enumerate(lane_types):
        row_items = [row["values"][lane_index] for row in rows]
        final_item = final.get(lane_index)
        if final_item is None:
            checks.append(
                {"lane_index": lane_index, "lane_type": lane_type, "status": "UNRESOLVED"}
            )
            continue
        if any(item["semantic_surface"] is None for item in row_items):
            checks.append(
                {
                    "lane_index": lane_index,
                    "lane_type": lane_type,
                    "status": "UNRESOLVED_MISSING_SEMANTIC_CELL_NOT_IMPUTED",
                }
            )
            continue
        if lane_type == "MONEY":
            addends = [money_integer_v1(item["semantic_surface"]) for item in row_items]
            target = money_integer_v1(final_item["semantic_surface"])
            status = (
                "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
                if None not in addends and target is not None and sum(addends) == target
                else "SEMANTIC_PROPOSAL_MISMATCH_REQUIRES_PIXEL_REVIEW"
            )
        else:
            addends_decimal = [_decimal_percentage(item["semantic_surface"]) for item in row_items]
            target_decimal = _decimal_percentage(final_item["semantic_surface"])
            status = (
                "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
                if None not in addends_decimal
                and target_decimal is not None
                and sum(addends_decimal, Decimal(0)) == target_decimal
                else "SEMANTIC_PROPOSAL_MISMATCH_REQUIRES_PIXEL_REVIEW"
            )
        checks.append({"lane_index": lane_index, "lane_type": lane_type, "status": status})
    return checks


def _region(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    owner_start: int,
    owner: Mapping[str, Any],
    *,
    enable_extended_owner_table_variants: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    owner_stop = owner["source_line_indices"][-1] + 1
    stop = _table_stop(
        lines,
        owner_stop,
        enable_extended_owner_table_variants=enable_extended_owner_table_variants,
    )
    labels = _label_candidates(
        lines,
        owner_stop,
        stop,
        enable_extended_owner_table_variants=enable_extended_owner_table_variants,
    )
    schema_roles = [item for item in labels if item["role"] in _SCHEMA_ELIGIBLE_ROLES]
    near = {
        "matched_roles": [item["role"] for item in labels],
        "owner_source_line_index": owner_start,
        "owner_surface": owner["surface"],
        "page_sequence": page["page_sequence"],
        "unresolved_reasons": [],
    }
    if len(schema_roles) < _MIN_SCHEMA_ROLE_COUNT:
        near["unresolved_reasons"] = ["INSUFFICIENT_DISTINCT_LOAN_TYPE_ROLES"]
        return None, near
    roles = [item["role"] for item in labels]
    if len(roles) != len(set(roles)):
        near["unresolved_reasons"] = ["DUPLICATE_LOAN_TYPE_ROLE"]
        return None, near
    first_label = min(item["source_line_indices"][0] for item in labels)
    periods, period_mode, lane_types, lane_centers, unit_scope, reasons = _axes(
        pages,
        page,
        owner_stop,
        owner,
        labels,
        enable_extended_owner_table_variants=enable_extended_owner_table_variants,
    )
    if not lane_types:
        near["unresolved_reasons"] = sorted(set(reasons))
        return None, near
    rows, totals, row_reasons = _rows_and_totals(
        page, labels, first_label, stop, lane_types, lane_centers
    )
    reasons.extend(row_reasons)
    if len(periods) != 2 or not totals:
        near["unresolved_reasons"] = sorted(set(reasons))
        return None, near
    graph = {
        "accounting_checks": _semantic_accounting(rows, totals),
        "branch": {
            "mode": "IMPLICIT_OWNER_IMMEDIATE_TYPED_TABLE",
            "schema_concept": "PHAN_TICH_THEO_LOAI_HINH_CHO_VAY",
        },
        "context_complete": not reasons,
        "intermediate_totals": totals[:-1],
        "lane_centers_x2": list(lane_centers),
        "lane_types": list(lane_types),
        "layout_mode": (
            "MONEY_PERCENT_COMPANION_LANES" if "PERCENT" in lane_types else "TWO_MONEY_LANES"
        ),
        "owner": canonical_clone_v1(owner),
        "page_sequence": page["page_sequence"],
        "period_axis": periods,
        "period_mode": period_mode,
        "rows": rows,
        "status": "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED",
        "table_source_line_range": [owner_start, stop - 1],
        "total": totals[-1],
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }
    return graph, near


def _scan(
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_owner_table_variants: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    graphs: list[dict[str, Any]] = []
    near: list[dict[str, Any]] = []
    for page in pages:
        lines = page["lines"]
        for start in range(len(lines)):
            owner = _owner_window(lines, start)
            if owner is None:
                continue
            graph, diagnostic = _region(
                pages,
                page,
                start,
                owner,
                enable_extended_owner_table_variants=enable_extended_owner_table_variants,
            )
            if graph is None:
                near.append(diagnostic)
            else:
                graphs.append(graph)
    deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
    for graph in graphs:
        key = (
            graph["page_sequence"],
            tuple(
                (row["role"], tuple(row["label"]["source_line_indices"])) for row in graph["rows"]
            ),
            tuple(item["source_line_index"] for item in graph["total"]),
        )
        current = deduplicated.get(key)
        if (
            current is None
            or graph["owner"]["source_line_indices"][-1]
            > current["owner"]["source_line_indices"][-1]
        ):
            deduplicated[key] = graph
    return list(deduplicated.values()), near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-type graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["graphs"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("loan-type graph identity/safety drifted")
    full_match_count = len(value["graphs"])
    expected_uniqueness = {
        "full_match_count": full_match_count,
        "status": (
            "UNIQUE_FULL_MATCH"
            if full_match_count == 1
            else "NO_FULL_MATCH"
            if full_match_count == 0
            else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
        ),
    }
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if full_match_count == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if full_match_count == 0
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_metrics = {
        "complete_owner_table_region_count": full_match_count,
        "near_region_count": len(value["near_regions"]),
        "semantic_accounting_corroborated_lane_count": sum(
            check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
            for graph in value["graphs"]
            for check in graph["accounting_checks"]
        ),
        "structurally_resolved_graph_count": sum(
            graph.get("status") == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            for graph in value["graphs"]
        ),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("loan-type graph status/metrics drifted")
    for graph in value["graphs"]:
        if (
            type(graph) is not dict
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or graph.get("branch", {}).get("mode") != "IMPLICIT_OWNER_IMMEDIATE_TYPED_TABLE"
            or type(graph.get("rows")) is not list
            or len(graph["rows"]) < _MIN_SCHEMA_ROLE_COUNT
            or type(graph.get("total")) is not list
            or not graph["total"]
            or type(graph.get("context_complete")) is not bool
            or graph["context_complete"] is not (not graph.get("unresolved_reasons"))
        ):
            raise _error("loan-type graph payload drifted")
        roles = [row.get("role") for row in graph["rows"]]
        if len(roles) != len(set(roles)) or any(role not in _ROLE_ALIASES for role in roles):
            raise _error("loan-type graph role axis drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ltvgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-type graph result identity drifted")
    return canonical_clone_v1(value)


def build_loan_type_variant_graph_document_v1(
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_owner_table_variants: bool = False,
) -> dict[str, Any]:
    """Enumerate and build every complete loan-type owner table in one PDF."""

    normalized_pages = _pages(pages)
    graphs, near = _scan(
        normalized_pages,
        enable_extended_owner_table_variants=enable_extended_owner_table_variants,
    )
    full_match_count = len(graphs)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": {
            "complete_owner_table_region_count": full_match_count,
            "near_region_count": len(near),
            "semantic_accounting_corroborated_lane_count": sum(
                check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
                for graph in graphs
                for check in graph["accounting_checks"]
            ),
            "structurally_resolved_graph_count": sum(
                graph["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED" for graph in graphs
            ),
        },
        "near_regions": near,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if full_match_count == 1
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if full_match_count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        ),
        "uniqueness": {
            "full_match_count": full_match_count,
            "status": (
                "UNIQUE_FULL_MATCH"
                if full_match_count == 1
                else "NO_FULL_MATCH"
                if full_match_count == 0
                else "AMBIGUOUS_MULTIPLE_FULL_MATCHES"
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "ltvgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_type_variant_graph_replay_v1(
    value: Any,
    pages: Sequence[Mapping[str, Any]],
    *,
    enable_extended_owner_table_variants: bool = False,
) -> dict[str, Any]:
    """Exact-rebuild a loan-type graph from the complete document line axis."""

    persisted = _validate_result(value)
    rebuilt = build_loan_type_variant_graph_document_v1(
        pages,
        enable_extended_owner_table_variants=enable_extended_owner_table_variants,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-type graph does not replay exactly")
    return rebuilt
