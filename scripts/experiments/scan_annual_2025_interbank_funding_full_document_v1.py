#!/usr/bin/env python3
"""Bank-blind whole-PDF scan for interbank deposit and borrowing notes.

This is the liability-side family rooted at TM ReportNormId 1040.  It is
deliberately separate from asset-side deposits-at and loans-to-other-credit-
institutions (root 575).  Bank, filename, note number and expected page never
participate in matching.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "ANNUAL_2025_INTERBANK_FUNDING_FULL_DOCUMENT_SCAN_V1"
FAMILY_ID = "INTERBANK_DEPOSITS_AND_BORROWINGS_LIABILITY"
SCAN_ID_PREFIX = "annual2025ifscanv1:scan:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_COMPLETE_PDF_BANK_BLIND_LIABILITY_SIDE_"
    "INTERBANK_DEPOSIT_BORROWING_OWNER_REQUIRED_DEMAND_TERM_BORROWING_CHILD_"
    "PERIOD_UNIT_GEOMETRY_CONTINUATION_NEGATIVE_CONTROL_STRUCTURE_ONLY"
)


class Annual2025InterbankFundingScanV1Error(ValueError):
    """The annual interbank-funding structure or replay drifted."""


def _error(message: str) -> Annual2025InterbankFundingScanV1Error:
    return Annual2025InterbankFundingScanV1Error(message)


def _n(value: Any) -> str:
    if type(value) is not str:
        raise _error("fresh VietOCR surface must be one exact string")
    return normalize_vietnamese_anchor_v1(value)


def _is_owner(text: str) -> bool:
    return (
        "tien gui" in text
        and "vay" in text
        and ("tctd" in text or "to chuc tin dung" in text or "to chuc tai chinh" in text)
        and "cho vay" not in text
        and "lai suat" not in text
        and "rui ro" not in text
        and "phan tich" not in text
        and "tai thoi diem" not in text
        and len(text.split()) <= 20
    )


def _is_demand(text: str) -> bool:
    return "tien gui khong ky han" in text and "lai suat" not in text


def _is_term(text: str) -> bool:
    return "tien gui co ky han" in text and "lai suat" not in text


def _is_deposit_parent(text: str) -> bool:
    return (
        "tien gui cua" in text
        and ("tctd" in text or "to chuc tin dung" in text)
        and "khong ky han" not in text
        and "co ky han" not in text
        and "lai suat" not in text
    )


def _is_borrowing(text: str) -> bool:
    return (
        "vay" in text
        and ("tctd" in text or "to chuc tin dung" in text or "to chuc tai chinh" in text)
        and "cho vay" not in text
        and "tien gui" not in text
        and "lai suat" not in text
        and "theo ky han" not in text
        and len(text.split()) <= 18
    )


def _period(text: str) -> bool:
    return (
        re.search(r"(?:30|31)[ /.-](?:03|3|06|6|12)[ /.-]20[0-9]{2}", text) is not None
        or "ngay 31 thang 12" in text
        or re.fullmatch(r"nam 20[0-9]{2}", text) is not None
        or text in {"so cuoi nam", "so dau nam"}
    )


def _unit(text: str) -> bool:
    return "trieu dong" in text or "trieu vnd" in text


def _line_ref(page: Mapping[str, Any], line: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bbox": list(line["source_bbox_raw_pixels"]),
        "page_sequence": page["physical_page"],
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _document(value: Any) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("pages")) is not list or not value["pages"]:
        raise _error("annual interbank scan requires one complete nonempty document")
    pages = []
    previous_page = 0
    for raw_page in value["pages"]:
        if type(raw_page) is not dict or type(raw_page.get("lines")) is not list:
            raise _error("annual interbank page shape drifted")
        number = raw_page.get("physical_page")
        if type(number) is not int or number != previous_page + 1:
            raise _error("annual interbank page sequence must be gap-free")
        lines = []
        previous_line = -1
        for raw_line in raw_page["lines"]:
            if type(raw_line) is not dict:
                raise _error("annual interbank line shape drifted")
            index = raw_line.get("source_line_index")
            bbox = raw_line.get("source_bbox_raw_pixels")
            text = raw_line.get("vietocr_text")
            if (
                type(index) is not int
                or index != previous_line + 1
                or type(bbox) is not list
                or len(bbox) != 4
                or any(type(item) is not int for item in bbox)
                or bbox[0] < 0
                or bbox[1] < 0
                or bbox[2] <= bbox[0]
                or bbox[3] <= bbox[1]
                or type(text) is not str
            ):
                raise _error("annual interbank line identity drifted")
            lines.append(
                {
                    "source_bbox_raw_pixels": list(bbox),
                    "source_line_index": index,
                    "vietocr_text": text,
                    "normalized_text": _n(text),
                }
            )
            previous_line = index
        pages.append({"physical_page": number, "lines": lines})
        previous_page = number
    return {"pages": pages}


def _window(
    pages: Sequence[Mapping[str, Any]], owner_page: int, owner_line: int
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    result = []
    for page in pages:
        number = page["physical_page"]
        if number < owner_page or number > owner_page + 1:
            continue
        for line in page["lines"]:
            if number == owner_page and line["source_line_index"] <= owner_line:
                continue
            if number == owner_page + 1 and _is_owner(line["normalized_text"]):
                # A repeated continuation owner belongs to the same region.
                continue
            result.append((page, line))
    return result


def _first(
    items: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]], predicate: Any
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    return next(((page, line) for page, line in items if predicate(line["normalized_text"])), None)


def _candidate(
    pages: Sequence[Mapping[str, Any]], owner_page: Mapping[str, Any], owner: Mapping[str, Any]
) -> dict[str, Any]:
    items = _window(pages, owner_page["physical_page"], owner["source_line_index"])
    demand = _first(items, _is_demand)
    term = _first(items, _is_term)
    borrowing = _first(items, _is_borrowing)
    parent = _first(items, _is_deposit_parent)
    reasons = []
    if demand is None:
        reasons.append("DEMAND_DEPOSIT_CHILD_MISSING")
    if term is None:
        reasons.append("TERM_DEPOSIT_CHILD_MISSING")
    if borrowing is None:
        reasons.append("BORROWING_CHILD_MISSING")
    if demand is not None and term is not None and borrowing is not None:
        demand_key = (demand[0]["physical_page"], demand[1]["source_line_index"])
        term_key = (term[0]["physical_page"], term[1]["source_line_index"])
        borrow_key = (borrowing[0]["physical_page"], borrowing[1]["source_line_index"])
        if max(demand_key, term_key) >= borrow_key:
            reasons.append("DEPOSIT_CHILDREN_DO_NOT_PRECEDE_BORROWING_CHILD")
    end_key = (
        (borrowing[0]["physical_page"], borrowing[1]["source_line_index"] + 45)
        if borrowing is not None
        else (owner_page["physical_page"] + 1, 10**9)
    )
    bounded = [
        (page, line)
        for page, line in items
        if (page["physical_page"], line["source_line_index"]) <= end_key
        and "lai suat" not in line["normalized_text"]
    ]
    periods = [_line_ref(page, line) for page, line in bounded if _period(line["normalized_text"])]
    units = [_line_ref(page, line) for page, line in bounded if _unit(line["normalized_text"])]
    period_columns = sorted(
        {
            round((item["bbox"][0] + item["bbox"][2]) / 2 / 40) * 40
            for item in periods
            if item["bbox"][0] > 700
        }
    )
    unit_columns = sorted(
        {
            round((item["bbox"][0] + item["bbox"][2]) / 2 / 40) * 40
            for item in units
            if item["bbox"][0] > 700
        }
    )
    if len(period_columns) < 2:
        reasons.append("TWO_PERIOD_COLUMNS_NOT_RESOLVED")
    if len(unit_columns) < 2:
        reasons.append("TWO_UNIT_COLUMNS_NOT_RESOLVED")
    role_refs = {
        "BORROWING": None if borrowing is None else _line_ref(*borrowing),
        "DEMAND_DEPOSIT": None if demand is None else _line_ref(*demand),
        "DEPOSIT_PARENT": None if parent is None else _line_ref(*parent),
        "OWNER": _line_ref(owner_page, owner),
        "TERM_DEPOSIT": None if term is None else _line_ref(*term),
    }
    return {
        "page_sequence_start": owner_page["physical_page"],
        "page_sequence_stop": (
            max(ref["page_sequence"] for ref in role_refs.values() if ref is not None)
        ),
        "period_axis_evidence": periods,
        "reasons": reasons,
        "role_refs": role_refs,
        "status": "COMPLETE" if not reasons else "NEAR",
        "unit_axis_evidence": units,
        "variant": (
            "EXPLICIT_DEPOSIT_PARENT" if parent is not None else "OWNER_DIRECT_DEPOSIT_CHILDREN"
        ),
    }


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "page_count_scanned": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    fields = {
        "claim_boundary",
        "family_id",
        "format_version",
        "metrics",
        "near_regions",
        "regions",
        "scan_id",
        "status",
        "uniqueness",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("annual interbank scan result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or value["uniqueness"]
        not in {"UNIQUE_COMPLETE_REGION", "NO_COMPLETE_REGION", "AMBIGUOUS_COMPLETE_REGIONS"}
    ):
        raise _error("annual interbank scan identity drifted")
    expected_metrics = _metrics(value["regions"], value["near_regions"])
    expected_metrics["page_count_scanned"] = value["metrics"].get("page_count_scanned")
    if (
        type(expected_metrics["page_count_scanned"]) is not int
        or expected_metrics["page_count_scanned"] <= 0
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("annual interbank scan metrics drifted")
    expected_uniqueness = (
        "UNIQUE_COMPLETE_REGION"
        if len(value["regions"]) == 1
        else "NO_COMPLETE_REGION"
        if not value["regions"]
        else "AMBIGUOUS_COMPLETE_REGIONS"
    )
    if value["uniqueness"] != expected_uniqueness:
        raise _error("annual interbank scan uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("scan_id")
    if identity != SCAN_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual interbank scan ID drifted")
    return canonical_clone_v1(value)


def build_annual_2025_interbank_funding_document_scan_v1(document: Any) -> dict[str, Any]:
    normalized = _document(document)
    candidates = []
    for page in normalized["pages"]:
        for line in page["lines"]:
            if _is_owner(line["normalized_text"]):
                candidates.append(_candidate(normalized["pages"], page, line))
    # A repeated continuation owner on the immediately following page is part
    # of the same physical region.  The first owner has the widest structure.
    reduced = []
    for candidate in candidates:
        if (
            reduced
            and candidate["page_sequence_start"] == reduced[-1]["page_sequence_stop"]
            and candidate["page_sequence_start"] == reduced[-1]["page_sequence_start"] + 1
        ):
            continue
        reduced.append(candidate)
    regions = [item for item in reduced if item["status"] == "COMPLETE"]
    near = [item for item in reduced if item["status"] == "NEAR"]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_region_count": len(regions),
            "near_region_count": len(near),
            "page_count_scanned": len(normalized["pages"]),
        },
        "near_regions": near,
        "regions": regions,
        "status": "ANNUAL_2025_INTERBANK_FUNDING_STRUCTURE_SCAN_COMPLETE",
        "uniqueness": (
            "UNIQUE_COMPLETE_REGION"
            if len(regions) == 1
            else "NO_COMPLETE_REGION"
            if not regions
            else "AMBIGUOUS_COMPLETE_REGIONS"
        ),
    }
    return _validate_result(
        {**material, "scan_id": SCAN_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_annual_2025_interbank_funding_document_scan_replay_v1(
    value: Any, document: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_annual_2025_interbank_funding_document_scan_v1(document)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual interbank scan does not replay exactly")
    return supplied
