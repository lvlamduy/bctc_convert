"""Bank-blind graph for other-payables and other-liabilities disclosures.

The common structure is an owner followed by internal and external payable
branches.  Employee, tax, other-payable, risk-provision, welfare-fund,
interest/fee and other intermediate branches are optional.  The matcher scans
one complete PDF, stops at nested owners and next-family boundaries, and never
uses bank, filename, page or note number as a routing condition.  Fresh
VietOCR text is anchor evidence only; numeric and mapping authority belongs to
the bounded verification layer.
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
    "OtherPayablesLiabilitiesVariantGraphV1Error",
    "build_other_payables_liabilities_variant_graph_document_v1",
    "validate_other_payables_liabilities_variant_graph_replay_v1",
]

FORMAT_VERSION = "OTHER_PAYABLES_LIABILITIES_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "OTHER_PAYABLES_AND_LIABILITIES"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_OTHER_PAYABLES_OWNER_INTERNAL_"
    "EXTERNAL_OPTIONAL_CHILD_PERIOD_UNIT_TOTAL_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_children_may_vary_without_bank_rules": True,
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
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|"
    r"(?:so\s+(?:du\s+)?(?:cuoi|dau)\s+(?:ky|nam))"
)
_OWNER_ALIASES = (
    "Các khoản phải trả và công nợ khác",
    "Các khoản nợ khác",
)
_MAX_REGION_LINES = 92


class OtherPayablesLiabilitiesVariantGraphV1Error(ValueError):
    """The complete-PDF input or other-payables graph drifted."""


def _error(message: str) -> OtherPayablesLiabilitiesVariantGraphV1Error:
    return OtherPayablesLiabilitiesVariantGraphV1Error(message)


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
        raise _error("other-payables matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("other-payables matcher page fields drifted")
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
                raise _error("other-payables line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
                or raw_line["semantic_text_source"] != "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
            ):
                raise _error("fresh VietOCR semantic text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
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
    value = re.sub(r"^(?:[0-9]+(?:[.][0-9]+)*[.)]?\s+)+", "", text).strip()
    return re.sub(r"\s+tiep theo$", "", value).strip(" :;.-")


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 12:
        return False
    return match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 18 and any(
        phrase in value
        for phrase in (
            "tinh hinh thuc hien nghia vu voi ngan sach",
            "von va quy cua to chuc tin dung",
            "von va cac quy",
            "bao cao tinh hinh thay doi von",
            "thue thu nhap hoan lai phai tra",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 18 or _is_owner(text):
        return None
    if "phai tra noi bo khac" in value:
        return "INTERNAL_OTHER"
    if "phai tra" in value and any(token in value for token in ("nhan vien", "can bo")):
        return "EMPLOYEE_PAYABLE"
    if "phai tra noi bo" in value:
        return "INTERNAL_PAYABLE"
    if "phai tra" in value and any(token in value for token in ("ben ngoai", "cho ben ngoai")):
        return "EXTERNAL_PAYABLE"
    if "thue" in value and any(token in value for token in ("nha nuoc", "ngan sach")):
        return "TAX_PAYABLE"
    if "du phong" in value and "rui ro khac" in value:
        return "OTHER_RISK_PROVISION"
    if "quy khen thuong" in value and "phuc loi" in value:
        return "WELFARE_FUND"
    if "cac khoan phai tra khac" in value:
        return "OTHER_PAYABLE"
    if "lai" in value and "phi phai tra" in value:
        return "INTEREST_AND_FEE_PAYABLE"
    if "thu nhap chua thuc hien" in value or "doanh thu cho phan" in value:
        return "UNEARNED_INCOME"
    return None


def _axis_role(text: str) -> str | None:
    if _DATE.search(text):
        return "PERIOD_AXIS"
    value = _strip_enumerator(text)
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    return None


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [line for page in pages for line in page["lines"]]


def _window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if (
            line["page_sequence"] != owner["page_sequence"]
            or _is_owner(line["normalized_text"])
            or _is_next_family(line["normalized_text"])
        ):
            break
        window.append(line)
    return window


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    owner = lines[start]
    window = _window(lines, start)
    events = [_line_ref(owner, "OWNER")]
    child_roles: set[str] = set()
    period_count = 0
    unit_count = 0
    numeric_count = 0
    for line in window:
        text = line["normalized_text"]
        child = _child_role(text)
        axis = _axis_role(text)
        if child is not None:
            child_roles.add(child)
            events.append(_line_ref(line, child))
        elif axis is not None:
            events.append(_line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
        if _NUMBER.fullmatch(text):
            numeric_count += 1
    core_roles = {"INTERNAL_PAYABLE", "EXTERNAL_PAYABLE"}
    complete = (
        core_roles.issubset(child_roles)
        and numeric_count >= 6
        and (period_count >= 2 or unit_count >= 1)
    )
    anchor_roles = ["OWNER", *sorted(child_roles)]
    pair_combinations = [list(pair) for pair in itertools.combinations(anchor_roles, 2)]
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "child_roles": sorted(child_roles),
            "optional_child_count": len(child_roles - core_roles),
            "period_axis_line_count": period_count,
            "presentation": "OWNER_THEN_FLEXIBLE_CHILD_ROWS_AND_PERIOD_VALUE_LANES",
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": numeric_count,
        "owner": _line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], owner["page_sequence"]],
        "pair_anchor_combinations": pair_combinations,
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
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("other-payables result fields drifted")
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
        raise _error("other-payables result identity or metrics drifted")
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
        raise _error("other-payables uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "oplivgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("other-payables graph identity drifted")
    return canonical_clone_v1(value)


def build_other_payables_liabilities_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every other-payables-like region in one complete PDF."""

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
        {**material, "result_id": "oplivgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_other_payables_liabilities_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_other_payables_liabilities_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-payables graph does not replay exactly")
    return supplied
