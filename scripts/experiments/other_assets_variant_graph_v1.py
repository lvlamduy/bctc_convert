"""Bank-blind complete-PDF graph for the ``Tài sản Có khác`` family.

The matcher starts with two-anchor combinations and admits three presentation
variants observed in the eight bound reports: one explicit umbrella spanning
one or more pages, adjacent receivable/other-asset sibling notes without a
printed umbrella, and one integrated table followed by labelled sub-tables.
Bank, filename, page and note identifiers are deliberately absent from all
matching decisions.  Fresh VietOCR text locates anchors only; pixels and the
upstream numeric axis remain mandatory in the later verification layer.
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
    "OtherAssetsVariantGraphV1Error",
    "build_other_assets_variant_graph_document_v1",
    "validate_other_assets_variant_graph_replay_v1",
]

FORMAT_VERSION = "OTHER_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "OTHER_ASSETS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_OTHER_ASSETS_EXPLICIT_UMBRELLA_"
    "SPLIT_SIBLING_NOTES_OR_INTEGRATED_SUBTABLE_STRUCTURE_ONLY_NO_NUMERIC_"
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
_MAX_REGION_LINES = 280
_MAX_REGION_PAGES = 3


class OtherAssetsVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed other-assets graph drifted."""


def _error(message: str) -> OtherAssetsVariantGraphV1Error:
    return OtherAssetsVariantGraphV1Error(message)


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
        raise _error("other-assets matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("other-assets matcher page fields drifted")
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
                "semantic_text",
                "semantic_text_source",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("other-assets line fields drifted")
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
    if not value_tokens or not expected_tokens:
        return False
    # Most lines in a complete report cannot possibly contain this anchor.
    # Reject them before the bounded phrase edit-distance loop.  This keeps the
    # matcher bank-blind while avoiding millions of irrelevant dynamic-program
    # comparisons over narrative pages.
    if not any(_edit_distance(token, expected_tokens[0]) <= 1 for token in value_tokens):
        return False
    for width in range(
        max(1, len(expected_tokens) - 1),
        min(len(value_tokens), len(expected_tokens) + 1) + 1,
    ):
        for start in range(len(value_tokens) - width + 1):
            if _edit_distance(" ".join(value_tokens[start : start + width]), expected) <= allowance:
                return True
    return False


def _strip_enumerator(text: str) -> str:
    value = re.sub(r"^(?:[0-9]+(?:[.]?[0-9]+)?\s+)+", "", text).strip()
    return re.sub(r"\s+tiep theo$", "", value).strip()


def _is_umbrella_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 7 and _near_phrase(value, "tai san co khac", allowance=2)


def _is_continuation_owner(text: str) -> bool:
    return _is_umbrella_owner(text) and "tiep theo" in text


def _is_receivable_owner(text: str) -> bool:
    value = _strip_enumerator(text)
    if any(term in value for term in ("noi bo", "ben ngoai", "khac", "chi tiet")):
        return False
    return len(value.split()) <= 5 and _near_phrase(value, "cac khoan phai thu", allowance=2)


def _is_next_family(text: str) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 15 and any(
        _near_phrase(value, phrase, allowance=2)
        for phrase in (
            "cac khoan no chinh phu va ngan hang nha nuoc",
            "tien gui va vay cac tctd khac",
            "tien vang gui va vay cac to chuc tin dung khac",
        )
    )


def _role(text: str) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 24:
        return None
    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("RECEIVABLE_INTERNAL", ("phai thu noi bo",)),
        ("RECEIVABLE_EXTERNAL", ("phai thu ben ngoai",)),
        ("RECEIVABLES", ("cac khoan phai thu",)),
        ("INTEREST_FEE_RECEIVABLES", ("cac khoan lai phi phai thu",)),
        ("OTHER_ASSET_BRANCH", ("tai san co khac",)),
        ("GOODWILL", ("loi the thuong mai",)),
        ("QUALITY", ("phan tich chat luong tai san co khac",)),
        ("CONSTRUCTION", ("xay dung co ban do dang", "mua sam tai san co dinh")),
        ("PREPAID", ("chi phi tra truoc", "chi phi cho phan bo")),
        ("MATERIAL", ("vat lieu",)),
        ("COLLATERAL_ASSET", ("tai san gan no", "tai san bao dam nhan thay the")),
        ("PAYMENT_RECEIVABLE", ("hoat dong thanh toan", "dich vu thanh toan")),
        ("DOCUMENT_RECEIVABLE", ("mien truy doi",)),
        ("DEPOSIT_INTEREST", ("lai phai thu tu tien gui",)),
        ("SECURITIES_INTEREST", ("lai phai thu tu dau tu chung khoan",)),
        ("CREDIT_INTEREST", ("lai phai thu tu hoat dong tin dung",)),
        ("DERIVATIVE_INTEREST", ("lai phai thu tu cong cu tai chinh phai sinh",)),
        ("GRADE_1", ("no du tieu chuan",)),
        ("GRADE_5", ("no co kha nang mat von",)),
        ("GOODWILL_OPEN", ("chua phan bo dau ky",)),
        ("GOODWILL_DECREASE", ("loi the thuong mai giam trong ky",)),
        ("GOODWILL_ALLOCATION", ("loi the thuong mai phan bo trong ky",)),
        ("GOODWILL_CLOSE", ("chua phan bo cuoi ky",)),
    )
    for role, phrases in checks:
        if any(_near_phrase(value, phrase, allowance=2) for phrase in phrases):
            return role
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


def _window(
    lines: Sequence[Mapping[str, Any]], start: int, *, stop_after_page: int | None = None
) -> list[Mapping[str, Any]]:
    owner = lines[start]
    window: list[Mapping[str, Any]] = []
    for line in lines[start + 1 : start + 1 + _MAX_REGION_LINES]:
        if line["page_sequence"] > owner["page_sequence"] + _MAX_REGION_PAGES - 1:
            break
        if stop_after_page is not None and line["page_sequence"] > stop_after_page:
            break
        if _is_next_family(line["normalized_text"]):
            break
        window.append(line)
    return window


def _integer_note_context(index: int, lines: Sequence[Mapping[str, Any]]) -> bool:
    if index == 0:
        return False
    target = lines[index]
    prior = lines[index - 1]
    return (
        prior["page_sequence"] == target["page_sequence"]
        and prior["bbox"][0] < target["bbox"][0]
        and min(prior["bbox"][3], target["bbox"][3]) > max(prior["bbox"][1], target["bbox"][1])
        and bool(re.fullmatch(r"[0-9]+", prior["normalized_text"]))
    )


def _region(
    owner_index: int,
    lines: Sequence[Mapping[str, Any]],
    *,
    presentation: str,
    split_other_index: int | None = None,
    integer_note_context: bool,
) -> dict[str, Any]:
    owner = lines[owner_index]
    window = _window(
        lines, owner_index, stop_after_page=owner["page_sequence"] if split_other_index else None
    )
    roles: dict[str, list[Mapping[str, Any]]] = {}
    periods: list[Mapping[str, Any]] = []
    units: list[Mapping[str, Any]] = []
    numeric: list[Mapping[str, Any]] = []
    for line in window:
        role = _role(line["normalized_text"])
        if role is not None:
            roles.setdefault(role, []).append(line)
        if _DATE.search(line["normalized_text"]):
            periods.append(line)
        if "trieu dong" in line["normalized_text"] or "trieu vnd" in line["normalized_text"]:
            units.append(line)
        if _NUMBER.fullmatch(line["normalized_text"].replace(" ", "")):
            numeric.append(line)
    if split_other_index is not None:
        roles.setdefault("OTHER_ASSET_BRANCH", []).append(lines[split_other_index])
    branch_roles = {
        role
        for role in roles
        if role
        in {"RECEIVABLES", "INTEREST_FEE_RECEIVABLES", "OTHER_ASSET_BRANCH", "GOODWILL", "QUALITY"}
    }
    detail_roles = set(roles) - branch_roles
    complete = (
        integer_note_context
        and bool(branch_roles)
        and len(detail_roles) >= 2
        and len(periods) >= 2
        and len(units) >= 2
        and len(numeric) >= 6
    )
    anchor_roles = ["OWNER", *sorted(branch_roles), *sorted(detail_roles)]
    events = [_line_ref(owner, "OWNER")]
    for role in sorted(roles):
        events.extend(_line_ref(item, role) for item in roles[role])
    events.extend(_line_ref(item, "PERIOD_AXIS") for item in periods[:10])
    events.extend(_line_ref(item, "UNIT_AXIS") for item in units[:10])
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": window[-1]["global_ordinal"] if window else owner["global_ordinal"],
        "events": events,
        "layout": {
            "branch_roles": sorted(branch_roles),
            "detail_roles": sorted(detail_roles),
            "explicit_unit_line_count": len(units),
            "integer_note_heading_context": integer_note_context,
            "period_axis_line_count": len(periods),
            "presentation": presentation,
        },
        "numeric_line_count": len(numeric),
        "owner": _line_ref(owner, "OWNER"),
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(anchor_roles, 2)
        ],
        "page_span": [
            owner["page_sequence"],
            window[-1]["page_sequence"] if window else owner["page_sequence"],
        ],
        "start_global_ordinal": owner["global_ordinal"],
    }


def _candidate_regions(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    lines = _flatten(pages)
    candidates: list[dict[str, Any]] = []
    covered_other_ordinals: set[int] = set()
    for index, line in enumerate(lines):
        if not _is_receivable_owner(line["normalized_text"]):
            continue
        if not _integer_note_context(index, lines):
            continue
        other_index = next(
            (
                cursor
                for cursor in range(index + 1, min(len(lines), index + 90))
                if lines[cursor]["page_sequence"] == line["page_sequence"]
                and _is_umbrella_owner(lines[cursor]["normalized_text"])
                and not _is_continuation_owner(lines[cursor]["normalized_text"])
            ),
            None,
        )
        if other_index is None:
            continue
        candidate = _region(
            index,
            lines,
            presentation="SPLIT_RECEIVABLE_AND_OTHER_ASSET_SIBLING_NOTES",
            split_other_index=other_index,
            integer_note_context=True,
        )
        if candidate["complete"]:
            covered_other_ordinals.add(lines[other_index]["global_ordinal"])
            candidates.append(candidate)
    for index, line in enumerate(lines):
        if (
            not _is_umbrella_owner(line["normalized_text"])
            or _is_continuation_owner(line["normalized_text"])
            or line["global_ordinal"] in covered_other_ordinals
        ):
            continue
        candidate = _region(
            index,
            lines,
            presentation="EXPLICIT_UMBRELLA_WITH_OPTIONAL_CONTINUATION_AND_SUBTABLES",
            integer_note_context=_integer_note_context(index, lines),
        )
        candidates.append(candidate)
    candidates.sort(key=lambda item: item["start_global_ordinal"])
    return candidates


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("other-assets graph result fields drifted")
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
        raise _error("other-assets graph identity or authority drifted")
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
        raise _error("other-assets graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "oavgv1:result:" + canonical_json_sha256_v1(material):
        raise _error("other-assets graph identity drifted")
    return canonical_clone_v1(value)


def build_other_assets_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate all other-assets regions in one complete PDF."""

    normalized_pages = _pages(pages)
    candidates = _candidate_regions(normalized_pages)
    regions = [item for item in candidates if item["complete"]]
    near_regions = [item for item in candidates if not item["complete"]]
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
        {**material, "result_id": "oavgv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_other_assets_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_other_assets_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-assets graph does not replay exactly")
    return supplied
