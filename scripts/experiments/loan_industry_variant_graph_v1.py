"""Bank-blind variable graph for customer-loan industry tables.

The matcher enumerates every fresh-VietOCR page and finds industry branches by
their accounting role, not by a bank, filename, note, or page.  It accepts a
variable/reordered subset of declarative industry roles, wrapped labels,
money/percentage companion lanes, relative periods, inherited units and
optional subtotal/margin populations.  Similar business-segment, enterprise,
deposit and loan-type tables remain negative candidates unless the complete
owner/branch/axis/row/total topology agrees.

Fresh VietOCR text is anchor evidence only.  Numeric and schema mapping
authority require a separate source-pixel review and accounting replay.
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
    "LoanIndustryVariantGraphV1Error",
    "build_loan_industry_variant_graph_document_v1",
    "validate_loan_industry_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_INDUSTRY_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "LOAN_INDUSTRY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CUSTOMER_LOAN_INDUSTRY_STRUCTURE_"
    "GEOMETRY_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_PROPOSAL_CORROBORATION_ONLY_"
    "TEXT_IS_ANCHOR_NO_SOURCE_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_BRANCH_ALIASES = (
    "Phân tích dư nợ cho vay theo ngành",
    "Phân tích dư nợ theo ngành",
    "Phân tích dư nợ theo ngành nghề kinh doanh",
    "Phân tích dư nợ cho vay theo ngành nghề kinh doanh",
    "Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh",
)
_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "AGRICULTURE_FORESTRY_FISHERY": (
        "Nông Lâm nghiệp, Thủy sản",
        "Nông nghiệp, lâm nghiệp và thủy sản",
        "Nông nghiệp, lâm nghiệp và thuỷ sản",
    ),
    "MINING": ("Khai khoáng",),
    "MANUFACTURING": ("Công nghiệp chế biến, chế tạo",),
    "UTILITIES": (
        "Sản xuất và phân phối điện, khí đốt, nước nóng, hơi nước và điều hòa không khí",
        "Sản xuất và phân phối điện, khí đốt, nước nóng, hơi nước và điều hoà không khí",
        "Sản xuất, phân phối điện, khí đốt và nước",
        "SXPP điện, khí đốt, nước nóng, hơi nước và điều hòa không khí",
        "Sản xuất và phân phối điện, khí đốt và nước nóng, hơi nước và điều hòa không khí",
    ),
    "WATER_WASTE": (
        "Cung cấp nước, QL&XL rác thải, nước thải",
        "Cung cấp nước; hoạt động quản lý và xử lý rác thải, nước thải",
        "Cung cấp nước, hoạt động quản lý và xử lý rác thải, nước thải",
    ),
    "CONSTRUCTION": ("Xây dựng",),
    "TRADE_REPAIR": (
        "Bán buôn, bán lẻ; sửa chữa ô tô, xe máy và xe có động cơ khác",
        "Bán buôn và bán lẻ; sửa chữa ô tô, mô tô, xe máy và xe có động cơ khác",
        "Bán buôn và bán lẻ; sửa chữa mô tô, ô tô, xe máy và xe có động cơ khác",
    ),
    "TRANSPORT_STORAGE": ("Vận tải, Kho bãi", "Vận tải kho bãi"),
    "ACCOMMODATION_FOOD": (
        "Dịch vụ lưu trú & ăn uống",
        "Dịch vụ lưu trú và ăn uống",
    ),
    "INFORMATION_COMMUNICATION": (
        "Thông tin & Truyền thông",
        "Thông tin và truyền thông",
    ),
    "FINANCE_BANKING_INSURANCE": (
        "Hoạt động tài chính, Ngân hàng, Bảo hiểm",
        "Hoạt động tài chính, ngân hàng và bảo hiểm",
        "Hoạt động tài chính và bảo hiểm",
    ),
    "REAL_ESTATE": ("Hoạt động kinh doanh Bất động sản",),
    "PROFESSIONAL_SCIENCE_TECHNOLOGY": (
        "Hoạt động chuyên môn, khoa học & công nghệ",
        "Hoạt động chuyên môn, khoa học và công nghệ",
    ),
    "ADMIN_SUPPORT": (
        "Hoạt động hành chính & Dịch vụ hỗ trợ",
        "Hoạt động hành chính và dịch vụ hỗ trợ",
    ),
    "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY": (
        "Hoạt động của Đảng cộng sản, tổ chức chính trị-xã hội, quản lý Nhà nước, an ninh quốc phòng, bảo đảm xã hội bắt buộc",
    ),
    "EDUCATION": ("Giáo dục & Đào tạo", "Giáo dục và đào tạo"),
    "HEALTH_SOCIAL_WORK": (
        "Y tế & hoạt động trợ giúp xã hội",
        "Y tế và hoạt động trợ giúp xã hội",
    ),
    "ARTS_ENTERTAINMENT": (
        "Nghệ thuật, vui chơi, giải trí",
        "Nghệ thuật, vui chơi và giải trí",
    ),
    "OTHER_SERVICES": ("Hoạt động dịch vụ khác",),
    "HOUSEHOLD_EMPLOYMENT_SELF_USE": (
        "Hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm vật chất và dịch vụ tự tiêu dùng của hộ gia đình",
        "Hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm vật chất và dịch vụ tiêu dùng của hộ gia đình",
        "Hoạt động làm thuê các công việc trong hộ gia đình, sản xuất sản phẩm vật chất và dịch vụ tiêu dùng của hộ gia đình",
    ),
    "FOREIGN_BRANCH_LOANS": ("Cho vay tại Chi nhánh và ngân hàng con nước ngoài",),
    "PERSONAL_HOUSING_LOANS": (
        "Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở",
    ),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "Cho vay giao dịch ký quỹ, ứng trước cho khách hàng",
        "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng",
    ),
    "BROAD_SERVICES": ("Dịch vụ",),
    "OTHER_INDUSTRIES": ("Khác", "Ngành khác"),
}
_SCHEMA_ELIGIBLE_ROLES = tuple(_ROLE_ALIASES)
_MIN_SCHEMA_ROLE_COUNT = 5
_MAX_OWNER_TABLE_LINE_SPAN = 180
_MAX_LABEL_WIDTH = 4
_BOUNDARY_PREFIXES = (
    "phan tich chat luong",
    "phan tich du no cho vay theo chat luong",
    "phan tich du no theo thoi",
    "phan tich du no cho vay theo thoi",
    "phan tich du no cho vay theo doi tuong",
    "phan tich du no theo doi tuong",
    "phan tich du no cho vay theo loai hinh doanh nghiep",
    "phan tich du no theo loai hinh doanh nghiep",
    "du phong rui ro cho vay khach hang",
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


class LoanIndustryVariantGraphV1Error(ValueError):
    """The complete-document semantic line axis or industry graph drifted."""


def _error(message: str) -> LoanIndustryVariantGraphV1Error:
    return LoanIndustryVariantGraphV1Error(message)


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
        raise _error("loan-industry scan requires one non-empty complete PDF page sequence")
    pages: list[dict[str, Any]] = []
    for page_offset, raw_page in enumerate(value):
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error(f"loan-industry page {page_offset} fields drifted")
        if type(raw_page["page_sequence"]) is not int or raw_page["page_sequence"] <= 0:
            raise _error("loan-industry page sequence drifted")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("loan-industry numeric authority flag drifted")
        if type(raw_page["lines"]) is not list:
            raise _error("loan-industry line axis drifted")
        lines: list[dict[str, Any]] = []
        for line_offset, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("loan-industry semantic line fields drifted")
            if (
                type(raw_line["source_line_index"]) is not int
                or raw_line["source_line_index"] != line_offset
                or type(raw_line["vietocr_text"]) is not str
                or (
                    raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str
                )
            ):
                raise _error("loan-industry semantic line identity/text drifted")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"], "loan-industry semantic line"),
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
        raise _error("loan-industry document pages must be unique and ordered")
    return pages


def _joined(lines: Sequence[Mapping[str, Any]], start: int, stop: int) -> str:
    return " ".join(line["vietocr_text"].strip() for line in lines[start:stop]).strip()


def _distinct_aliases(values: Sequence[str]) -> tuple[str, ...]:
    """Keep one surface per accentless alias without changing source evidence."""

    distinct: dict[str, str] = {}
    for value in values:
        distinct.setdefault(normalize_vietnamese_anchor_v1(value), value)
    return tuple(distinct.values())


def _branch_surface(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value)
    normalized = re.sub(r"^(?:\d+\s+)+", "", normalized)
    normalized = re.sub(r"\s+tiep theo$", "", normalized)
    return normalized


def _branch_window(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any] | None:
    first_normalized = _branch_surface(lines[start]["vietocr_text"])
    if not first_normalized.startswith("phan tich"):
        return None
    aliases = [normalize_vietnamese_anchor_v1(alias) for alias in _BRANCH_ALIASES]
    for width in range(1, min(_MAX_LABEL_WIDTH, len(lines) - start) + 1):
        surface = _joined(lines, start, start + width)
        normalized = _branch_surface(surface)
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


def _loan_owner_surface(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value)
    normalized = re.sub(r"^(?:\d+\s+)+", "", normalized)
    normalized = re.sub(r"\s+tiep theo$", "", normalized)
    return normalized


def _customer_loan_context(
    pages: Sequence[Mapping[str, Any]],
    page: Mapping[str, Any],
    first_label: int,
) -> dict[str, Any] | None:
    aliases = tuple(
        normalize_vietnamese_anchor_v1(value)
        for value in (
            "Cho vay khách hàng",
            "Các khoản cho vay khách hàng",
            "Dư nợ cho vay khách hàng",
            "Dư nợ cho vay khách hàng của Ngân hàng",
        )
    )

    def candidates(
        candidate_page: Mapping[str, Any], start: int, stop: int
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        lines = candidate_page["lines"]
        for line_index in range(start, stop):
            for width in range(1, min(3, stop - line_index) + 1):
                surface = _joined(lines, line_index, line_index + width)
                normalized = _loan_owner_surface(surface)
                if (
                    normalized in aliases
                    or match_vietnamese_anchor_alias_v1(normalized, aliases) is not None
                ):
                    result.append(
                        {
                            "mode": "SAME_PAGE_CUSTOMER_LOAN_OWNER",
                            "page_sequence": candidate_page["page_sequence"],
                            "source_line_indices": list(range(line_index, line_index + width)),
                            "surface": surface,
                        }
                    )
        return result

    local = candidates(page, 0, first_label)
    if local:
        return local[-1]
    page_offset = next(
        (
            offset
            for offset, candidate in enumerate(pages)
            if candidate["page_sequence"] == page["page_sequence"]
        ),
        None,
    )
    if page_offset is not None and page_offset > 0:
        previous = pages[page_offset - 1]
        if previous["page_sequence"] == page["page_sequence"] - 1:
            inherited = candidates(previous, 0, len(previous["lines"]))
            if inherited:
                selected = inherited[-1]
                selected["mode"] = "IMMEDIATE_PREVIOUS_PAGE_CUSTOMER_LOAN_OWNER"
                return selected
    return None


def _is_boundary(text: str) -> bool:
    normalized = normalize_vietnamese_anchor_v1(text)
    return any(normalized.startswith(prefix) for prefix in _BOUNDARY_PREFIXES)


def _table_stop(lines: Sequence[Mapping[str, Any]], branch_stop: int) -> int:
    hard_stop = min(len(lines), branch_stop + _MAX_OWNER_TABLE_LINE_SPAN)
    for index in range(branch_stop, hard_stop):
        if _is_boundary(lines[index]["vietocr_text"]):
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


def _label_candidates(
    lines: Sequence[Mapping[str, Any]], start: int, stop: int
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    occupied: set[int] = set()
    for line_index in range(start, stop):
        if line_index in occupied:
            continue
        if is_number_like_v1(lines[line_index]["vietocr_text"]):
            continue
        text_indices: list[int] = []
        for candidate_index in range(line_index, min(stop, line_index + 9)):
            if not is_number_like_v1(lines[candidate_index]["vietocr_text"]):
                text_indices.append(candidate_index)
                if len(text_indices) == _MAX_LABEL_WIDTH:
                    break
        proposals: list[tuple[list[int], str, str, str]] = []
        for width in range(1, len(text_indices) + 1):
            indices = text_indices[:width]
            surface = " ".join(lines[index]["vietocr_text"].strip() for index in indices).strip()
            # A standalone/embedded ``8`` is a common visual OCR rendering of
            # ``&`` in Vietnamese table labels.  Removing it is punctuation
            # normalization only; the original surface remains in evidence.
            match_surface = surface.replace("8", "&")
            for role, aliases in _ROLE_ALIASES.items():
                kind = match_vietnamese_anchor_alias_v1(match_surface, _distinct_aliases(aliases))
                if kind is not None:
                    proposals.append((indices, role, kind, surface))
        if not proposals:
            continue
        # Prefer the longest wrapped label, then the exact match.  A role may
        # occur only once inside an accepted owner table.
        indices, role, kind, surface = max(
            proposals,
            key=lambda item: (len(item[0]), item[2] == "EXACT_ACCENTLESS_ALIAS"),
        )
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
    first_label: int,
) -> tuple[list[dict[str, Any]], str, list[str], list[int], dict[str, Any], list[str]]:
    header = page["lines"][owner_stop:first_label]
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


def _row_bands(labels: Sequence[Mapping[str, Any]]) -> list[tuple[int, int]]:
    centers = [item["y_center_x2"] for item in labels]
    bands: list[tuple[int, int]] = []
    for index, center in enumerate(centers):
        if index == 0:
            next_gap = centers[1] - center if len(centers) > 1 else 120
            lower = center - max(40, next_gap // 2)
        else:
            lower = (centers[index - 1] + center) // 2
        if index + 1 == len(centers):
            previous_gap = center - centers[index - 1] if index else 120
            upper = center + max(40, previous_gap // 2)
        else:
            upper = (center + centers[index + 1]) // 2
        bands.append((lower, upper))
    return bands


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
    assigned: set[int] = set()
    rows: list[dict[str, Any]] = []
    for label in labels:
        by_lane: dict[int, Mapping[str, Any]] = {}
        duplicates: set[int] = set()
        for line in lines[first_line:stop]:
            if not is_number_like_v1(line["vietocr_text"]):
                continue
            numeric_center_x2 = line["bbox"][1] + line["bbox"][3]
            if not 2 * label["bbox"][1] <= numeric_center_x2 <= 2 * label["bbox"][3]:
                continue
            lane = _nearest_lane(center_x2_v1(line), lane_centers)
            if lane is None:
                continue
            if lane in by_lane:
                duplicates.add(lane)
            else:
                by_lane[lane] = line
        if duplicates:
            reasons.append(f"DUPLICATE_ROW_LANES_{label['role']}")
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
                assigned.add(line["source_line_index"])
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

    remaining: list[Mapping[str, Any]] = []
    for line in lines[first_line:stop]:
        if (
            line["source_line_index"] not in assigned
            and is_number_like_v1(line["vietocr_text"])
            and _nearest_lane(center_x2_v1(line), lane_centers) is not None
        ):
            remaining.append(line)
    remaining.sort(key=lambda line: (line["bbox"][1] + line["bbox"][3], center_x2_v1(line)))
    heights = [line["bbox"][3] - line["bbox"][1] for line in remaining]
    tolerance = max(20, (sorted(heights)[len(heights) // 2] if heights else 20) * 2)
    clusters: list[list[Mapping[str, Any]]] = []
    for line in remaining:
        center = line["bbox"][1] + line["bbox"][3]
        if not clusters:
            clusters.append([line])
            continue
        previous_center = clusters[-1][0]["bbox"][1] + clusters[-1][0]["bbox"][3]
        if abs(center - previous_center) <= tolerance:
            clusters[-1].append(line)
        else:
            clusters.append([line])

    totals: list[list[dict[str, Any]]] = []
    for cluster in clusters:
        by_lane: dict[int, Mapping[str, Any]] = {}
        for line in cluster:
            lane = _nearest_lane(center_x2_v1(line), lane_centers)
            if lane is not None and lane not in by_lane:
                by_lane[lane] = line
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
    branch_start: int,
    branch: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    lines = page["lines"]
    branch_stop = branch["source_line_indices"][-1] + 1
    stop = _table_stop(lines, branch_stop)
    labels = _label_candidates(lines, branch_stop, stop)
    schema_roles = [item for item in labels if item["role"] in _SCHEMA_ELIGIBLE_ROLES]
    near = {
        "branch_source_line_index": branch_start,
        "branch_surface": branch["surface"],
        "matched_roles": [item["role"] for item in labels],
        "page_sequence": page["page_sequence"],
        "unresolved_reasons": [],
    }
    if len(schema_roles) < _MIN_SCHEMA_ROLE_COUNT:
        near["unresolved_reasons"] = ["INSUFFICIENT_DISTINCT_LOAN_INDUSTRY_ROLES"]
        return None, near
    roles = [item["role"] for item in labels]
    if len(roles) != len(set(roles)):
        near["unresolved_reasons"] = ["DUPLICATE_LOAN_INDUSTRY_ROLE"]
        return None, near
    first_label = min(item["source_line_indices"][0] for item in labels)
    periods, period_mode, lane_types, lane_centers, unit_scope, reasons = _axes(
        pages, page, branch_stop, first_label
    )
    customer_loan_context = _customer_loan_context(pages, page, first_label)
    if customer_loan_context is None:
        reasons.append("CUSTOMER_LOAN_OWNER_CONTEXT_NOT_RESOLVED")
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
    accounting_checks = _semantic_accounting(rows, totals)
    if customer_loan_context is None:
        near["unresolved_reasons"] = sorted(set(reasons))
        return None, near
    graph = {
        "accounting_checks": accounting_checks,
        "branch": {
            **canonical_clone_v1(branch),
            "schema_concept": "PHAN_TICH_THEO_NGANH_NGHE_KINH_DOANH",
        },
        "context_complete": not reasons,
        "customer_loan_context": customer_loan_context,
        "intermediate_totals": totals[:-1],
        "lane_centers_x2": list(lane_centers),
        "lane_types": list(lane_types),
        "layout_mode": (
            "MONEY_PERCENT_COMPANION_LANES" if "PERCENT" in lane_types else "TWO_MONEY_LANES"
        ),
        "page_sequence": page["page_sequence"],
        "period_axis": periods,
        "period_mode": period_mode,
        "rows": rows,
        "status": "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED",
        "table_source_line_range": [branch_start, stop - 1],
        "total": totals[-1],
        "unit_scope": unit_scope,
        "unresolved_reasons": sorted(set(reasons)),
    }
    return graph, near


def _scan(pages: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    graphs: list[dict[str, Any]] = []
    near: list[dict[str, Any]] = []
    for page in pages:
        lines = page["lines"]
        for start in range(len(lines)):
            branch = _branch_window(lines, start)
            if branch is None:
                continue
            graph, diagnostic = _region(pages, page, start, branch)
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
            or graph["branch"]["source_line_indices"][-1]
            > current["branch"]["source_line_indices"][-1]
        ):
            deduplicated[key] = graph
    return list(deduplicated.values()), near


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-industry graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["graphs"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("loan-industry graph identity/safety drifted")
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
        "complete_branch_table_region_count": full_match_count,
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
        raise _error("loan-industry graph status/metrics drifted")
    for graph in value["graphs"]:
        if (
            type(graph) is not dict
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or type(graph.get("branch")) is not dict
            or set(graph["branch"])
            != {"match_kind", "schema_concept", "source_line_indices", "surface"}
            or graph["branch"]["schema_concept"] != "PHAN_TICH_THEO_NGANH_NGHE_KINH_DOANH"
            or graph["branch"].get("match_kind")
            not in {"EXACT_ACCENTLESS_ALIAS", "ONE_EDIT_ALIAS_IN_COMPLETE_TOPOLOGY"}
            or type(graph.get("customer_loan_context")) is not dict
            or set(graph["customer_loan_context"])
            != {"mode", "page_sequence", "source_line_indices", "surface"}
            or type(graph.get("rows")) is not list
            or len(graph["rows"]) < _MIN_SCHEMA_ROLE_COUNT
            or type(graph.get("total")) is not list
            or not graph["total"]
            or type(graph.get("context_complete")) is not bool
            or graph["context_complete"] is not (not graph.get("unresolved_reasons"))
        ):
            raise _error("loan-industry graph payload drifted")
        roles = [row.get("role") for row in graph["rows"]]
        if len(roles) != len(set(roles)) or any(role not in _ROLE_ALIASES for role in roles):
            raise _error("loan-industry graph role axis drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "livgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-industry graph result identity drifted")
    return canonical_clone_v1(value)


def build_loan_industry_variant_graph_document_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Enumerate every complete customer-loan industry table in one PDF."""

    normalized_pages = _pages(pages)
    graphs, near = _scan(normalized_pages)
    full_match_count = len(graphs)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "graphs": graphs,
        "metrics": {
            "complete_branch_table_region_count": full_match_count,
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
        {**material, "result_id": "livgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_industry_variant_graph_replay_v1(
    value: Any, pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Exact-rebuild an industry graph from the complete document line axis."""

    persisted = _validate_result(value)
    rebuilt = build_loan_industry_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-industry graph does not replay exactly")
    return rebuilt
