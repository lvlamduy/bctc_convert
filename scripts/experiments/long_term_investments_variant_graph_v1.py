"""Bank-blind full-PDF graph for other long-term investments.

The live TM family starts at ReportNormId 862 and ends at 5959, immediately
before tangible fixed assets (868).  Source reports may expose only an
``other long-term investment`` row, split that row into organization/project
and fund children, or add joint-venture and associate populations.  Those
branches are optional; the owner, at least one accounting child, the period
axis and a trailing net total form the common core.

Fresh VietOCR Transformer text is used only to locate anchors.  Numbers,
signs, DASH cells, period/unit scope and accounting equations are verified by
the bounded pixel-review layer.  Bank, filename, page and note number are not
matching inputs.
"""

from __future__ import annotations

import itertools
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

__all__ = [
    "FORMAT_VERSION",
    "LongTermInvestmentsVariantGraphV1Error",
    "build_long_term_investments_variant_graph_document_v1",
    "validate_long_term_investments_variant_graph_replay_v1",
]

FORMAT_VERSION = "LONG_TERM_INVESTMENTS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "OTHER_LONG_TERM_INVESTMENTS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_LONG_TERM_INVESTMENT_OWNER_"
    "OPTIONAL_JOINT_VENTURE_ASSOCIATE_OTHER_ORGANIZATION_PROJECT_FUND_"
    "PROVISION_TRAILING_NET_TOTAL_AND_NEXT_FAMILY_BOUNDARY_STRUCTURE_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
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
    "trailing_total_and_accounting_replay_required_for_mapping": True,
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
    r"(?:so\s+(?:cuoi|dau)\s+ky)"
)
_MAX_REGION_LINES = 180
_MAX_REGION_PAGES = 2


class LongTermInvestmentsVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed long-term-investment graph drifted."""


def _error(message: str) -> LongTermInvestmentsVariantGraphV1Error:
    return LongTermInvestmentsVariantGraphV1Error(message)


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
        raise _error("long-term-investment matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("long-term-investment matcher page fields drifted")
        page_sequence = raw_page["page_sequence"]
        if type(page_sequence) is not int or page_sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be exact and gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines: list[dict[str, Any]] = []
        for line_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("long-term-investment line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if type(raw_line["vietocr_text"]) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["vietocr_text"]),
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


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _near_phrase(value: str, expected: str, *, allowance: int = 2) -> bool:
    if expected in value:
        return True
    value_tokens = value.split()
    expected_tokens = expected.split()
    for width in range(
        max(1, len(expected_tokens) - 1),
        min(len(value_tokens), len(expected_tokens) + 1) + 1,
    ):
        for start in range(len(value_tokens) - width + 1):
            if _edit_distance(" ".join(value_tokens[start : start + width]), expected) <= allowance:
                return True
    return False


def _strip_enumerator(text: str) -> str:
    return re.sub(r"^(?:[0-9]+(?:[.]?[0-9]+)?\s+)+", "", text).strip()


def _is_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return (
        value.startswith("gop ")
        and len(value.split()) <= 10
        and _near_phrase(value, "gop von dau tu dai han", allowance=2)
    )


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 11 and any(
        _near_phrase(value, phrase, allowance=2)
        for phrase in (
            "tang giam tai san co dinh huu hinh",
            "tai san co dinh huu hinh",
            "cac khoan no chinh phu va ngan hang",
        )
    )


def _child_role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if "danh sach" in value or len(value.split()) > 14:
        return None
    if _near_phrase(value, "dau tu vao cong ty lien doanh", allowance=3):
        return "JOINT_VENTURE"
    if _near_phrase(value, "dau tu vao cong ty lien ket", allowance=3):
        return "ASSOCIATE"
    if "du phong" in value and any(term in value for term in ("dau tu", "gop von", "giam gia")):
        return "PROVISION"
    if any(term in value for term in ("to chuc kinh te", "du an dai han")):
        return "ORGANIZATION_PROJECT"
    if "quy dau tu" in value:
        return "INVESTMENT_FUND"
    if _near_phrase(value, "dau tu dai han khac", allowance=2):
        return "OTHER_LONG_TERM"
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


def _region(owner_index: int, lines: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    owner = lines[owner_index]
    window: list[Mapping[str, Any]] = []
    for line in lines[owner_index + 1 : owner_index + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] > owner["page_sequence"] + _MAX_REGION_PAGES - 1:
            break
        if _is_next_family(line["normalized_text"]):
            break
        if _is_owner(line["normalized_text"]):
            break
        window.append(line)
    children: dict[str, list[Mapping[str, Any]]] = {}
    periods: list[Mapping[str, Any]] = []
    units: list[Mapping[str, Any]] = []
    numeric_lines: list[Mapping[str, Any]] = []
    for line in window:
        text = line["normalized_text"]
        role = _child_role(text)
        if role is not None:
            children.setdefault(role, []).append(line)
        if _DATE.search(text):
            periods.append(line)
        if "trieu dong" in text or "trieu vnd" in text:
            units.append(line)
        if _NUMBER.fullmatch(text.replace(" ", "")):
            numeric_lines.append(line)
    core_children = {
        role: values
        for role, values in children.items()
        if role in {"JOINT_VENTURE", "ASSOCIATE", "OTHER_LONG_TERM", "ORGANIZATION_PROJECT"}
    }
    complete = bool(core_children) and len(periods) >= 2 and len(numeric_lines) >= 3
    anchors = ["OWNER", *sorted(core_children)]
    pair_combinations = [list(pair) for pair in itertools.combinations(anchors, 2)]
    events = [_line_ref(owner, "OWNER")]
    for role in sorted(children):
        events.extend(_line_ref(line, role) for line in children[role])
    events.extend(_line_ref(line, "PERIOD_AXIS") for line in periods[:4])
    events.extend(_line_ref(line, "UNIT_AXIS") for line in units[:2])
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": window[-1]["global_ordinal"] if window else owner["global_ordinal"],
        "events": events,
        "layout": {
            "child_roles": sorted(children),
            "explicit_unit_line_count": len(units),
            "period_axis_line_count": len(periods),
            "presentation": (
                "ORGANIZATION_DETAIL_WITH_OWNERSHIP_AXIS"
                if "ORGANIZATION_PROJECT" in children and "OTHER_LONG_TERM" not in children
                else "PARENT_CHILD_ROWS_WITH_PERIOD_COLUMNS"
            ),
        },
        "numeric_line_count": len(numeric_lines),
        "owner": _line_ref(owner, "OWNER"),
        "pair_anchor_combinations": pair_combinations,
        "page_span": [
            owner["page_sequence"],
            window[-1]["page_sequence"] if window else owner["page_sequence"],
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("long-term-investment graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("long-term-investment graph identity or authority drifted")
    complete_count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if complete_count == 1
        else (
            "UNRESOLVED_NO_COMPLETE_REGION"
            if complete_count == 0
            else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
        )
    )
    expected_uniqueness = {
        "complete_region_count": complete_count,
        "status": "UNIQUE_FULL_MATCH" if complete_count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    expected_metrics = {
        "complete_region_count": complete_count,
        "near_region_count": len(value["near_regions"]),
        "owner_candidate_count": complete_count + len(value["near_regions"]),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("long-term-investment graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ltivgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("long-term-investment graph identity drifted")
    return canonical_clone_v1(value)


def build_long_term_investments_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every complete and near-complete family region in one PDF."""

    normalized_pages = _pages(pages)
    lines = _flatten(normalized_pages)
    candidates = [
        _region(index, lines)
        for index, line in enumerate(lines)
        if _is_owner(line["normalized_text"])
    ]
    regions = [candidate for candidate in candidates if candidate["complete"]]
    near_regions = [candidate for candidate in candidates if not candidate["complete"]]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "complete_region_count": len(regions),
            "near_region_count": len(near_regions),
            "owner_candidate_count": len(candidates),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            if len(regions) == 1
            else (
                "UNRESOLVED_NO_COMPLETE_REGION"
                if not regions
                else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
            )
        ),
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "NOT_UNIQUE_FULL_MATCH",
        },
    }
    return _validate_result(
        {**material, "result_id": "ltivgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_long_term_investments_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Rebuild the graph from the complete PDF and require typed equality."""

    supplied = _validate_result(value)
    rebuilt = build_long_term_investments_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("long-term-investment graph does not replay exactly")
    return supplied
