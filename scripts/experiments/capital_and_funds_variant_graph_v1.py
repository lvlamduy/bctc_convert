"""Bank-blind graph for capital-and-funds disclosures.

The common core is an equity owner followed by a statement-of-changes heading,
capital plus at least two other equity/fund columns, opening/closing balance
axes and numeric cells.  Share-count, EPS, treasury-share, NCI, FX and
increase/decrease branches are optional.  The matcher scans one complete PDF,
may cross one continuation page, and never uses bank, filename, page or note
number as a routing condition.  Fresh VietOCR is semantic anchor evidence
only; numeric and schema authority belongs to the bounded review layer.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

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
    "CapitalAndFundsVariantGraphV1Error",
    "build_capital_and_funds_variant_graph_document_v1",
    "validate_capital_and_funds_variant_graph_replay_v1",
]

FORMAT_VERSION = "CAPITAL_AND_FUNDS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CAPITAL_AND_FUNDS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CAPITAL_FUNDS_OWNER_STATEMENT_OF_"
    "CHANGES_CORE_EQUITY_CHILD_OPEN_CLOSE_PERIOD_UNIT_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_and_movement_rows_may_vary_without_bank_rules": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
    "topology_period_unit_total_and_accounting_replay_required_for_mapping": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "family_id",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_OWNER_ALIASES = (
    "Vốn và các quỹ",
    "Vốn và quỹ",
    "Vốn và quỹ của Tổ chức tín dụng",
    "Vốn chủ sở hữu",
)
_CHANGE_HEADING_ALIASES = (
    "Báo cáo tình hình thay đổi vốn chủ sở hữu",
    "Báo cáo thay đổi vốn và các quỹ hợp nhất",
    "Báo cáo thay đổi vốn và các quỹ",
    "Tình hình thay đổi vốn chủ sở hữu",
)
_MAX_REGION_LINES = 230


class CapitalAndFundsVariantGraphV1Error(ValueError):
    """The complete-PDF input or capital-and-funds graph drifted."""


def _error(message: str) -> CapitalAndFundsVariantGraphV1Error:
    return CapitalAndFundsVariantGraphV1Error(message)


def _bbox(value: Any) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("line bbox must contain four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("capital-and-funds matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("capital-and-funds matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines = []
        for line_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "semantic_text",
                "semantic_text_source",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("capital-and-funds line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
                or raw_line["semantic_text_source"]
                not in {
                    "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                    "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE",
                }
            ):
                raise _error("fresh VietOCR semantic text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
                    "semantic_text_source": raw_line["semantic_text_source"],
                    "source_line_index": line_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = page_sequence
    return pages


def _strip_enumerator(text: str) -> str:
    value = re.sub(r"^(?:[0-9]+(?:[.][0-9]+)*[.)]?[ :]*)+", "", text).strip()
    value = re.sub(r"\s+(?:tiep theo|hop nhat)$", "", value).strip()
    return value.strip(" :;.-")


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 12:
        return False
    return match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None


def _is_change_heading(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 14 and (
        match_vietnamese_anchor_alias_v1(value, _CHANGE_HEADING_ALIASES) is not None
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 20:
        return False
    return any(
        phrase in value
        for phrase in (
            "thu nhap lai va cac khoan thu nhap tuong tu",
            "thu nhap lai thuan",
            "tinh hinh thuc hien nghia vu voi ngan sach",
            "chi phi thue thu nhap doanh nghiep",
            "tai san giay to co gia the chap",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 14 or _is_owner(text) or _is_change_heading(text):
        return None
    if value in {"von dieu le", "von gop von dieu le", "von gop"}:
        return "CAPITAL"
    if "thang du von co phan" in value:
        return "SHARE_PREMIUM"
    if value in {"von khac", "von chu so huu khac"}:
        return "OTHER_CAPITAL"
    if "co phieu quy" in value:
        return "TREASURY_SHARES"
    if "quy du tru bo sung von" in value:
        return "CAPITAL_RESERVE"
    if "quy du phong tai chinh" in value:
        return "FINANCIAL_RESERVE"
    if "quy dau tu phat trien" in value:
        return "DEVELOPMENT_FUND"
    if "quy khac" in value and "thuoc von" in value:
        return "OTHER_RESERVES"
    if value in {"quy khac", "cac quy khac"}:
        return "OTHER_RESERVES"
    if "chenh lech ty gia" in value:
        return "FX_DIFFERENCE"
    if "loi nhuan" in value and "chua phan" in value:
        return "RETAINED_EARNINGS"
    if "loi ich" in value and "khong kiem soat" in value:
        return "NONCONTROLLING_INTEREST"
    if value in {"tong", "tong cong", "von chu so huu"}:
        return "TOTAL"
    if "lai" in value and "moi co phieu" in value:
        return "EPS_BRANCH"
    if value == "co phieu" or "chi tiet co phieu" in value:
        return "SHARE_DETAIL_BRANCH"
    return None


def _movement_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 16:
        return None
    if value in {"du dau", "so du dau ky", "so du dau nam"}:
        return "OPENING_BALANCE"
    if value in {"du cuoi", "so du cuoi ky", "so du cuoi nam"}:
        return "CLOSING_BALANCE"
    if value in {"tang", "trich lap tang", "phat sinh trong nam tang"}:
        return "INCREASE"
    if value in {"giam", "su dung giam", "phat sinh trong nam giam"}:
        return "DECREASE"
    if re.match(r"^(?:so du )?tai ngay 0?1(?: thang |[./ ])0?1", value):
        return "OPENING_BALANCE"
    if re.match(r"^(?:so du )?tai ngay 31(?: thang |[./ ])12", value):
        return "INTERMEDIATE_OR_OPENING_BALANCE"
    if re.match(
        r"^(?:so du )?tai ngay (?:30(?: thang |[./ ])0?6|31(?: thang |[./ ])0?3)",
        value,
    ):
        return "CLOSING_BALANCE"
    if value == "so du":
        return "BALANCE_AXIS"
    return None


def _axis_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    if re.fullmatch(r"(?:0?1[./])?0?1[./](?:20)?2[0-9]", value):
        return "OPENING_PERIOD_AXIS"
    if re.fullmatch(r"(?:30[./]0?6|31[./]0?3|31[./]12)[./](?:20)?2[0-9]", value):
        return "CLOSING_PERIOD_AXIS"
    return None


def _column_header_composites(
    window: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Recompose stacked table-column headers without using bank/layout IDs."""

    composites: list[dict[str, Any]] = []
    for page_sequence in sorted({line["page_sequence"] for line in window}):
        page_lines = [line for line in window if line["page_sequence"] == page_sequence]
        unit_lines = [
            line for line in page_lines if _axis_role(line["normalized_text"]) == "UNIT_AXIS"
        ]
        if not unit_lines:
            continue
        first_unit_y = min(line["bbox"][1] for line in unit_lines)
        header_lines = [
            line
            for line in page_lines
            if first_unit_y - 210 <= line["bbox"][1] < first_unit_y
            and not _NUMBER.fullmatch(line["normalized_text"])
            and _axis_role(line["normalized_text"]) is None
            and not _is_owner(line["normalized_text"])
            and not _is_change_heading(line["normalized_text"])
        ]
        clusters: list[dict[str, Any]] = []
        for line in sorted(header_lines, key=lambda item: (item["bbox"][1], item["bbox"][0])):
            center = (line["bbox"][0] + line["bbox"][2]) / 2
            compatible = [
                cluster
                for cluster in clusters
                if abs(center - cluster["center_sum"] / len(cluster["lines"])) <= 72
            ]
            if compatible:
                cluster = min(
                    compatible,
                    key=lambda item: abs(center - item["center_sum"] / len(item["lines"])),
                )
                cluster["lines"].append(line)
                cluster["center_sum"] += center
            else:
                clusters.append({"center_sum": center, "lines": [line]})
        for cluster in clusters:
            lines = sorted(cluster["lines"], key=lambda item: (item["bbox"][1], item["bbox"][0]))
            normalized = " ".join(line["normalized_text"] for line in lines).strip()
            role = _child_role(normalized)
            if role is None or len(lines) < 2:
                continue
            composites.append(
                {
                    "normalized_text": normalized,
                    "page_sequence": page_sequence,
                    "role": role,
                    "source_line_indices": [line["source_line_index"] for line in lines],
                    "vietocr_text_parts": [line["vietocr_text"] for line in lines],
                }
            )
    return composites


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "semantic_text_source": line["semantic_text_source"],
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [line for page in pages for line in page["lines"]]


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] > owner["page_sequence"] + 1:
            break
        if _is_next_family(line["normalized_text"]):
            break
        if _is_owner(line["normalized_text"]):
            value = _strip_enumerator(line["normalized_text"])
            if "tiep theo" not in line["normalized_text"] and value != _strip_enumerator(
                owner["normalized_text"]
            ):
                break
        window.append(line)
    return window


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    owner = lines[start]
    window = _window(lines, start)
    events = [_line_ref(owner, "OWNER")]
    child_roles: set[str] = set()
    movement_roles: set[str] = set()
    change_heading_count = 0
    unit_count = 0
    numeric_count = 0
    rotated_line_count = int(
        owner["semantic_text_source"] == "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
    )
    header_composites = _column_header_composites(window)
    child_roles.update(item["role"] for item in header_composites)
    for line in window:
        text = line["normalized_text"]
        if _is_change_heading(text):
            change_heading_count += 1
            events.append(_line_ref(line, "STATEMENT_OF_CHANGES"))
        else:
            child = _child_role(text)
            movement = _movement_role(text)
            axis = _axis_role(text)
            if child is not None:
                child_roles.add(child)
                events.append(_line_ref(line, child))
            elif movement is not None:
                movement_roles.add(movement)
                events.append(_line_ref(line, movement))
            elif axis is not None:
                events.append(_line_ref(line, axis))
                unit_count += axis == "UNIT_AXIS"
                movement_roles.add(axis)
        numeric_count += bool(_NUMBER.fullmatch(text))
        rotated_line_count += int(
            line["semantic_text_source"] == "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
        )
    equity_core = child_roles & {
        "SHARE_PREMIUM",
        "OTHER_CAPITAL",
        "CAPITAL_RESERVE",
        "FINANCIAL_RESERVE",
        "DEVELOPMENT_FUND",
        "OTHER_RESERVES",
        "FX_DIFFERENCE",
        "RETAINED_EARNINGS",
        "NONCONTROLLING_INTEREST",
    }
    opening_seen = bool(
        movement_roles
        & {
            "OPENING_BALANCE",
            "OPENING_PERIOD_AXIS",
            "BALANCE_AXIS",
            "INTERMEDIATE_OR_OPENING_BALANCE",
        }
    )
    closing_seen = bool(movement_roles & {"CLOSING_BALANCE", "CLOSING_PERIOD_AXIS", "BALANCE_AXIS"})
    complete = (
        change_heading_count >= 1
        and "CAPITAL" in child_roles
        and len(equity_core) >= 2
        and opening_seen
        and closing_seen
        and numeric_count >= 10
        and unit_count >= 1
    )
    anchor_roles = [
        "OWNER",
        *(["STATEMENT_OF_CHANGES"] if change_heading_count else []),
        *sorted(child_roles),
        *sorted(movement_roles),
    ]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "change_heading_count": change_heading_count,
            "child_roles": sorted(child_roles),
            "column_header_composites": header_composites,
            "movement_roles": sorted(movement_roles),
            "optional_child_count": len(child_roles - {"CAPITAL"}),
            "presentation": "OWNER_CHANGE_HEADING_FLEXIBLE_EQUITY_COLUMNS_MOVEMENT_ROWS",
            "rotated_rescue_line_count": rotated_line_count,
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": numeric_count,
        "owner": _line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], end["page_sequence"]],
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(dict.fromkeys(anchor_roles), 2)
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "numeric_line_count_in_complete_regions": sum(
            item["numeric_line_count"] for item in regions
        ),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "rotated_rescue_line_count_in_complete_regions": sum(
            item["layout"]["rotated_rescue_line_count"] for item in regions
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("capital-and-funds result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("capital-and-funds result identity or metrics drifted")
    complete_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if complete_count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_uniqueness = {
        "complete_region_count": complete_count,
        "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("capital-and-funds uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cafvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("capital-and-funds graph identity drifted")
    return canonical_clone_v1(value)


def build_capital_and_funds_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every capital-and-funds-like region in one complete PDF."""

    parsed_pages = _pages(pages)
    lines = _flatten(parsed_pages)
    candidates = [
        _region(lines, index)
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"])
    ]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(regions) == 1
        else "UNRESOLVED_NO_UNIQUE_REGION",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "cafvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_capital_and_funds_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_capital_and_funds_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("capital-and-funds graph does not replay exactly")
    return supplied
