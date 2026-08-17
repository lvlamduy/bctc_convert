"""Bank-blind graph for issued valuable-paper disclosure variants.

The graph starts from the common issued-paper owner and accepts variable
instrument, tenor, valuation and period/unit layouts.  It is intentionally
agnostic to bank, filename, page and note number.  Fresh VietOCR text is only
an anchor proposal; pixel, numeric, accounting and schema authority remain in
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
    "IssuedValuablePapersVariantGraphV1Error",
    "build_issued_valuable_papers_variant_graph_document_v1",
    "validate_issued_valuable_papers_variant_graph_replay_v1",
]

FORMAT_VERSION = "ISSUED_VALUABLE_PAPERS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "ISSUED_VALUABLE_PAPERS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_ISSUED_VALUABLE_PAPERS_OWNER_"
    "INSTRUMENT_TENOR_OPTIONAL_VALUATION_PERIOD_UNIT_STRUCTURE_ONLY_NO_NUMERIC_"
    "SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_instrument_and_axis_branches_may_vary_without_bank_rules": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
    "topology_period_unit_valuation_total_and_accounting_replay_required_for_mapping": True,
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
    "Phát hành giấy tờ có giá",
    "Phát hành giấy tờ có giá thông thường",
    "Phát hành giấy tờ có giá thông thường không bao gồm công cụ tài chính phức hợp",
)
_CERTIFICATE_ALIASES = ("Chứng chỉ tiền gửi",)
_MAX_REGION_LINES = 80


class IssuedValuablePapersVariantGraphV1Error(ValueError):
    """The complete-PDF input or issued-paper graph drifted."""


def _error(message: str) -> IssuedValuablePapersVariantGraphV1Error:
    return IssuedValuablePapersVariantGraphV1Error(message)


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
        raise _error("issued-paper matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("issued-paper matcher page fields drifted")
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
                raise _error("issued-paper line fields drifted")
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
    value = re.sub(r"^(?:[0-9]+[.)]?\s+)+", "", text).strip()
    return re.sub(r"\s+tiep theo$", "", value).strip(" :;.-")


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    if len(value.split()) > 18:
        return False
    return match_vietnamese_anchor_alias_v1(value, _OWNER_ALIASES) is not None


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 15 and any(
        phrase in value
        for phrase in (
            "cac khoan phai tra va cong no khac",
            "cac khoan no khac",
            "von va quy cua to chuc tin dung",
        )
    )


def _instrument_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 12 or _is_owner(text):
        return None
    if value.startswith("chung chi tien gui") or (
        match_vietnamese_anchor_alias_v1(value, _CERTIFICATE_ALIASES) is not None
    ):
        return "CERTIFICATE_OF_DEPOSIT"
    if "ky phieu" in value and "trai phieu" in value:
        return "PROMISSORY_AND_BOND_COMBINED"
    if match_vietnamese_anchor_alias_v1(value, ("Kỳ phiếu",)) is not None:
        return "PROMISSORY_NOTE"
    if "trai phieu" in value and not any(
        phrase in value for phrase in ("lai suat", "bao gom", "phat hanh ngay")
    ):
        return "BOND"
    return None


def _tenor_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 12:
        return None
    if any(
        phrase in value
        for phrase in (
            "duoi 12 thang",
            "duoi 1 nam",
            "duoi mot nam",
            "tu 12 thang tro xuong",
            "ngan han",
        )
    ):
        return "TENOR_SHORT"
    if any(
        phrase in value
        for phrase in (
            "tu 12 thang den duoi 5 nam",
            "tu tren 12 thang den 5 nam",
            "tu 1 nam den 2 nam",
            "tu mot nam den hai nam",
            "ky han 3 nam",
            "ky han ba nam",
            "ky han 5 nam",
            "ky han nam nam",
            "duoi 5 nam",
            "trung han",
            "tren 12 thang",
        )
    ):
        return "TENOR_MEDIUM_OR_UNSPLIT_OVER_12"
    if any(
        phrase in value
        for phrase in (
            "tren 5 nam",
            "tu 5 nam tro len",
            "tu 05 nam tro len",
            "ky han 10 nam",
            "ky han muoi nam",
            "dai han",
        )
    ):
        return "TENOR_LONG"
    return None


def _axis_role(text: str) -> str | None:
    if _DATE.search(text):
        return "PERIOD_AXIS"
    value = _strip_enumerator(text)
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    if value in {"gia tri ghi so", "menh gia", "chiet khau", "phu troi"}:
        return "VALUATION_AXIS"
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
        if line["page_sequence"] != owner["page_sequence"] or _is_next_family(
            line["normalized_text"]
        ):
            break
        window.append(line)
    return window


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
    owner = lines[start]
    window = _window(lines, start)
    events = [_line_ref(owner, "OWNER")]
    instrument_roles: set[str] = set()
    tenor_roles: set[str] = set()
    period_count = 0
    unit_count = 0
    valuation_count = 0
    numeric_count = 0
    for line in window:
        text = line["normalized_text"]
        instrument = _instrument_role(text)
        tenor = _tenor_role(text)
        axis = _axis_role(text)
        if instrument is not None:
            instrument_roles.add(instrument)
            events.append(_line_ref(line, instrument))
        if tenor is not None:
            tenor_roles.add(tenor)
            events.append(_line_ref(line, tenor))
        if instrument is None and tenor is None and axis is not None:
            events.append(_line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
            valuation_count += axis == "VALUATION_AXIS"
        if _NUMBER.fullmatch(text):
            numeric_count += 1
    complete = (
        bool(instrument_roles and tenor_roles)
        and numeric_count >= 4
        and (unit_count >= 1 or period_count >= 2 or valuation_count >= 2)
    )
    anchor_roles = ["OWNER", *sorted(instrument_roles), *sorted(tenor_roles)]
    pair_combinations = [list(pair) for pair in itertools.combinations(anchor_roles, 2)]
    presentation = "VARIABLE_INSTRUMENT_TENOR_PERIOD_LAYOUT"
    if len(instrument_roles) >= 3 and period_count == 0:
        presentation = "TENOR_ROWS_BY_INSTRUMENT_COLUMNS"
    elif valuation_count >= 2 and period_count <= 1:
        presentation = "SINGLE_PERIOD_BOOK_VALUE_AND_FACE_VALUE"
    elif "PROMISSORY_AND_BOND_COMBINED" in instrument_roles:
        presentation = "COMBINED_PROMISSORY_AND_BOND_PARENT"
    end = window[-1] if window else owner
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "instrument_roles": sorted(instrument_roles),
            "period_axis_line_count": period_count,
            "presentation": presentation,
            "tenor_roles": sorted(tenor_roles),
            "unit_axis_line_count": unit_count,
            "valuation_axis_line_count": valuation_count,
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


def _is_continuation_region(region: Mapping[str, Any]) -> bool:
    owner_text = normalize_vietnamese_anchor_v1(region["owner"]["vietocr_text"])
    return "tiep theo" in owner_text


def _merge_adjacent_continuation_regions(
    candidates: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = 0
    while index < len(candidates):
        current = canonical_clone_v1(candidates[index])
        if index + 1 < len(candidates):
            following = candidates[index + 1]
            current_instruments = set(current["layout"]["instrument_roles"])
            following_instruments = set(following["layout"]["instrument_roles"])
            current_tenors = set(current["layout"]["tenor_roles"])
            following_tenors = set(following["layout"]["tenor_roles"])
            is_one_table_continuation = (
                current["complete"]
                and following["complete"]
                and following["owner"]["page_sequence"] == current["owner"]["page_sequence"] + 1
                and _is_continuation_region(following)
                and current_instruments == following_instruments
                and current_tenors == following_tenors
            )
            if is_one_table_continuation:
                anchor_roles = sorted(
                    set(current["anchor_roles"]) | set(following["anchor_roles"]),
                    key=lambda role: (role != "OWNER", role),
                )
                current["anchor_roles"] = anchor_roles
                current["end_global_ordinal"] = following["end_global_ordinal"]
                current["events"].extend(canonical_clone_v1(following["events"]))
                current["layout"] = {
                    "instrument_roles": sorted(current_instruments),
                    "period_axis_line_count": (
                        current["layout"]["period_axis_line_count"]
                        + following["layout"]["period_axis_line_count"]
                    ),
                    "presentation": "ADJACENT_PERIOD_TABLE_CONTINUATION",
                    "tenor_roles": sorted(current_tenors),
                    "unit_axis_line_count": (
                        current["layout"]["unit_axis_line_count"]
                        + following["layout"]["unit_axis_line_count"]
                    ),
                    "valuation_axis_line_count": (
                        current["layout"]["valuation_axis_line_count"]
                        + following["layout"]["valuation_axis_line_count"]
                    ),
                }
                current["numeric_line_count"] += following["numeric_line_count"]
                current["page_span"] = [
                    current["page_span"][0],
                    following["page_span"][1],
                ]
                current["pair_anchor_combinations"] = [
                    list(pair) for pair in itertools.combinations(anchor_roles, 2)
                ]
                index += 1
        merged.append(current)
        index += 1
    return merged


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("issued-paper result fields drifted")
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
        raise _error("issued-paper result identity or metrics drifted")
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
        raise _error("issued-paper uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ivpvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("issued-paper graph identity drifted")
    return canonical_clone_v1(value)


def build_issued_valuable_papers_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every issued-paper-like region in one complete PDF."""

    parsed_pages = _pages(pages)
    lines = _flatten(parsed_pages)
    candidates = _merge_adjacent_continuation_regions(
        [
            _region(lines, index)
            for index, line in enumerate(lines)
            if _is_owner(line["normalized_text"])
        ]
    )
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
        {**material, "result_id": "ivpvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_issued_valuable_papers_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_issued_valuable_papers_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("issued-paper graph does not replay exactly")
    return supplied
