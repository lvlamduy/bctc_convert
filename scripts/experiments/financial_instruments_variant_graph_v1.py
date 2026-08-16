"""Bank-blind variant graph for financial-instrument carrying/fair values."""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "FINANCIAL_INSTRUMENTS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "FINANCIAL_INSTRUMENTS_CARRYING_AND_FAIR_VALUE"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_PAIR_FIRST_OWNER_BOOK_FAIR_"
    "HEADERS_ASSET_LIABILITY_ROWS_UNIT_AND_NUMERIC_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fair_value_asterisk_interpreted_as_zero": False,
    "fresh_vietocr_transformer_text_required": True,
    "interest_or_currency_risk_table_can_accept": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "row_order_required_for_matching": False,
    "text_similarity_alone_can_accept": False,
}
_FIELDS = {
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
_ASSET_ROLES = {
    "ASSET_CASH",
    "ASSET_CENTRAL_BANK",
    "ASSET_DERIVATIVE",
    "ASSET_INTERBANK",
    "ASSET_INVESTMENT_SECURITIES",
    "ASSET_LOANS",
    "ASSET_LONG_TERM_INVESTMENT",
    "ASSET_OTHER",
    "ASSET_TRADING_SECURITIES",
}
_LIABILITY_ROLES = {
    "LIABILITY_CENTRAL_AND_INTERBANK",
    "LIABILITY_CUSTOMER_DEPOSITS",
    "LIABILITY_DERIVATIVE",
    "LIABILITY_ENTRUSTED_CAPITAL",
    "LIABILITY_GOVERNMENT",
    "LIABILITY_INTERBANK",
    "LIABILITY_ISSUED_PAPERS",
    "LIABILITY_OTHER",
}


class FinancialInstrumentsVariantGraphV1Error(ValueError):
    """The complete-PDF input or financial-instruments graph drifted."""


def _error(message: str) -> FinancialInstrumentsVariantGraphV1Error:
    return FinancialInstrumentsVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_financial_instruments"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name("interest_income_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error("cannot load common accounting graph support")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strip(text: str) -> str:
    return _support()._strip_enumerator(text).lstrip("-+ ").strip()


def _owner(text: str) -> bool:
    value = _strip(text)
    return (
        "thuyet minh cong cu tai chinh" in value
        or (
            "tai san tai chinh" in value
            and ("no phai tra tai chinh" in value or "cong no tai chinh" in value)
        )
        or (
            "cac cong cu tai chinh" in value
            and "trinh bay chi tiet" in value
            and "bang duoi day" in value
        )
    )


def _book_header(text: str) -> bool:
    return "gia tri ghi so" in _strip(text)


def _fair_header(text: str) -> bool:
    return "gia tri hop ly" in _strip(text)


def _unit(text: str) -> bool:
    value = _strip(text)
    return "trieu dong" in value or "trieu vnd" in value


def _negative_axis(text: str) -> str | None:
    value = _strip(text)
    if "rui ro tien te" in value or "usd duoc quy doi" in value:
        return "CURRENCY_RISK"
    if "rui ro lai suat" in value or "dinh gia lai lai suat" in value:
        return "INTEREST_RATE_RISK"
    if "rui ro thanh khoan" in value or "thoi han thanh toan" in value:
        return "LIQUIDITY_RISK"
    return None


def _role(text: str) -> str | None:
    value = _strip(text)
    if "tien mat" in value and ("vang bac" in value or "da quy" in value):
        return "ASSET_CASH"
    if "tien gui tai nhnn" in value:
        return "ASSET_CENTRAL_BANK"
    if "tien gui" in value and "cho vay" in value and "tctd" in value:
        return "ASSET_INTERBANK"
    if "chung khoan kinh doanh" in value:
        return "ASSET_TRADING_SECURITIES"
    if "cho vay khach hang" in value:
        return "ASSET_LOANS"
    if "chung khoan" in value and (
        "dau tu" in value or "san sang de ban" in value or "giu den ngay dao han" in value
    ):
        return "ASSET_INVESTMENT_SECURITIES"
    if "gop von" in value or "dau tu dai han" in value:
        return "ASSET_LONG_TERM_INVESTMENT"
    if "tai san tai chinh khac" in value:
        return "ASSET_OTHER"
    if "cong cu tai chinh phai sinh" in value and (
        "tai san tai chinh" in value or "khoan no tai chinh" in value
    ):
        return "DERIVATIVE_ROW"
    if "no chinh phu" in value or ("no" in value and "nhnn" in value):
        return "LIABILITY_GOVERNMENT"
    if "tien gui" in value and "vay" in value and "nhnn" in value and "tctd" in value:
        return "LIABILITY_CENTRAL_AND_INTERBANK"
    if "tien gui" in value and "vay" in value and "tctd" in value:
        return "LIABILITY_INTERBANK"
    if "tien gui cua khach hang" in value:
        return "LIABILITY_CUSTOMER_DEPOSITS"
    if "von tai tro" in value and "uy thac" in value:
        return "LIABILITY_ENTRUSTED_CAPITAL"
    if "phat hanh giay to co gia" in value:
        return "LIABILITY_ISSUED_PAPERS"
    if "cac khoan no" in value and ("khac" in value or "tai chinh khac" in value):
        return "LIABILITY_OTHER"
    return None


def _joined_roles(pages: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    support = _support()
    roles: list[str] = []
    events: list[dict[str, Any]] = []
    section: str | None = None
    for page in pages:
        lines = page["lines"]
        for index, line in enumerate(lines):
            candidates = [line["normalized_text"]]
            if index + 1 < len(lines):
                candidates.append(f"{candidates[-1]} {lines[index + 1]['normalized_text']}")
            if index + 2 < len(lines):
                candidates.append(f"{candidates[-1]} {lines[index + 2]['normalized_text']}")
            role = next((found for value in candidates if (found := _role(value))), None)
            if role is not None:
                if role == "DERIVATIVE_ROW":
                    role = "LIABILITY_DERIVATIVE" if section == "LIABILITY" else "ASSET_DERIVATIVE"
                elif role in _ASSET_ROLES:
                    section = "ASSET"
                elif role in _LIABILITY_ROLES:
                    section = "LIABILITY"
                roles.append(role)
                events.append(support._line_ref(line, role))
    return list(dict.fromkeys(roles)), events


def _region(
    owner_page: Mapping[str, Any],
    table_page: Mapping[str, Any],
    owner: Mapping[str, Any],
) -> dict[str, Any]:
    support = _support()
    pages = [owner_page] if owner_page is table_page else [owner_page, table_page]
    roles, events = _joined_roles(pages)
    table_texts = [line["normalized_text"] for line in table_page["lines"]]
    book_lines = [line for line in table_page["lines"] if _book_header(line["normalized_text"])]
    fair_lines = [line for line in table_page["lines"] if _fair_header(line["normalized_text"])]
    unit_lines = [line for line in table_page["lines"] if _unit(line["normalized_text"])]
    negative_axes = list(
        dict.fromkeys(
            axis
            for page in pages
            for line in page["lines"]
            if (axis := _negative_axis(line["normalized_text"])) is not None
        )
    )
    numeric_count = sum(support._NUMBER.fullmatch(text) is not None for text in table_texts)
    observed = set(roles)
    asset_count = len(observed & _ASSET_ROLES)
    liability_count = len(observed & _LIABILITY_ROLES)
    complete = (
        bool(book_lines)
        and bool(fair_lines)
        and bool(unit_lines)
        and asset_count >= 6
        and liability_count >= 4
        and numeric_count >= 12
    )
    anchors = ["FAMILY_OWNER", "BOOK_HEADER", "FAIR_HEADER", *sorted(observed)]
    events = [
        support._line_ref(owner, "FAMILY_OWNER"),
        *[support._line_ref(line, "BOOK_HEADER") for line in book_lines],
        *[support._line_ref(line, "FAIR_HEADER") for line in fair_lines],
        *[support._line_ref(line, "UNIT_AXIS") for line in unit_lines],
        *events,
    ]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": table_page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "asset_role_count": asset_count,
            "book_and_fair_headers_observed": bool(book_lines and fair_lines),
            "liability_role_count": liability_count,
            "negative_risk_axes_observed": negative_axes,
            "observed_source_roles": roles,
            "row_order_is_semantic": False,
            "table_continues_from_previous_page": owner_page is not table_page,
        },
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "FAMILY_OWNER"),
        "page_span": [owner_page["page_sequence"], table_page["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": owner_page["lines"][0]["global_ordinal"],
    }


def _candidates(
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    regions: list[dict[str, Any]] = []
    near: list[dict[str, Any]] = []
    support = _support()
    for index, table_page in enumerate(pages):
        book = any(_book_header(line["normalized_text"]) for line in table_page["lines"])
        fair = any(_fair_header(line["normalized_text"]) for line in table_page["lines"])
        if not (book or fair):
            continue
        possible_owner_pages = [table_page]
        if index:
            possible_owner_pages.append(pages[index - 1])
        owner_match = next(
            (
                (owner_page, line)
                for owner_page in possible_owner_pages
                for line in owner_page["lines"]
                if _owner(line["normalized_text"])
            ),
            None,
        )
        if owner_match is None:
            near.append(
                {
                    "book_header_observed": book,
                    "fair_header_observed": fair,
                    "page_span": [table_page["page_sequence"], table_page["page_sequence"]],
                    "reason": "BOOK_OR_FAIR_HEADER_WITHOUT_BOUND_FAMILY_OWNER",
                }
            )
            continue
        region = _region(owner_match[0], table_page, owner_match[1])
        (regions if region["complete"] else near).append(
            region
            if region["complete"]
            else {
                "book_header_observed": book,
                "fair_header_observed": fair,
                "owner": support._line_ref(owner_match[1], "FAMILY_OWNER"),
                "page_span": region["page_span"],
                "reason": "OWNER_AND_HEADERS_WITH_INSUFFICIENT_ASSET_LIABILITY_DEPTH",
            }
        )
    return regions, near


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {page for region in regions for page in region["page_span"]}
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("financial-instruments graph fields drifted")
    regions = value["regions"]
    near = value["near_regions"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["status"] != "FINANCIAL_INSTRUMENTS_GRAPH_ENUMERATION_COMPLETE"
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(regions) is not list
        or type(near) is not list
        or not same_typed_json_v1(value["metrics"], _metrics(regions, near))
    ):
        raise _error("financial-instruments graph identity drifted")
    expected_uniqueness = {
        "complete_region_count": len(regions),
        "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if not same_typed_json_v1(value["uniqueness"], expected_uniqueness):
        raise _error("financial-instruments uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "fivgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("financial-instruments graph ID drifted")
    return canonical_clone_v1(value)


def build_financial_instruments_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    support = _support()
    checked = support._pages(pages)
    regions, near = _candidates(checked)
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": "FINANCIAL_INSTRUMENTS_GRAPH_ENUMERATION_COMPLETE",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate(
        {**material, "result_id": "fivgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_financial_instruments_variant_graph_document_v1(value: Any) -> dict[str, Any]:
    return _validate(value)
