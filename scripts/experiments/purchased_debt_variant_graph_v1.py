"""Bank-blind complete-PDF graph for the purchased-debt note family.

The live TM interval is ReportNormId 800 through 5739, immediately before
ReportNormId 804 (investment securities).  A complete source cluster starts at
``Hoạt động mua nợ`` and contains the balance block

``Mua nợ bằng VND`` [optionally ``Mua nợ bằng ngoại tệ``]
``Dự phòng rủi ro`` -> unlabeled net total,

followed by the detail block ``Nợ gốc đã mua`` and ``Lãi của khoản nợ đã
mua``.  Quality and provision-movement tables may follow as non-additive
branches.  The next investment-securities heading closes the region, including
when it occurs on the following page.

Fresh VietOCR Transformer text is anchor evidence only.  Numeric values,
period/unit scope, DASH cells, accounting equations and schema mapping require
an independent visible-PDF replay.  No bank, filename, page or note number is a
matching condition.
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
    "PurchasedDebtVariantGraphV1Error",
    "build_purchased_debt_variant_graph_document_v1",
    "validate_purchased_debt_variant_graph_replay_v1",
]

FORMAT_VERSION = "PURCHASED_DEBT_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "PURCHASED_DEBT_ACTIVITY"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_PURCHASED_DEBT_OWNER_BALANCE_"
    "CURRENCY_PROVISION_NET_DETAIL_PRINCIPAL_INTEREST_OPTIONAL_QUALITY_OR_"
    "PROVISION_MOVEMENT_FIRST_LAST_NEXT_FAMILY_BOUNDARY_STRUCTURE_ONLY_NO_"
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
    "optional_branch_can_be_added_to_core_balance": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "sibling_order_fixed": False,
    "text_similarity_alone_can_accept": False,
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
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9]\s+nam\s+20[0-9]{2})|"
    r"(?:so\s+(?:cuoi|dau)\s+ky)"
)
_MAX_REGION_PAGES = 3
_MAX_REGION_LINES = 260
_CORE_ROLES = ("owner", "purchase_vnd", "provision", "principal", "interest")


class PurchasedDebtVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed purchased-debt graph drifted."""


def _error(message: str) -> PurchasedDebtVariantGraphV1Error:
    return PurchasedDebtVariantGraphV1Error(message)


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
        raise _error("line bbox must be four exact positive-bound integers")
    return list(value)


def _pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("purchased-debt matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    global_ordinal = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("purchased-debt matcher page fields drifted")
        sequence = raw_page["page_sequence"]
        if type(sequence) is not int or sequence != previous_page + 1:
            raise _error("complete PDF page sequence must be gap-free")
        if type(raw_page["primary_numeric_authority"]) is not bool:
            raise _error("primary numeric authority flag must be exact bool")
        if type(raw_page["lines"]) is not list:
            raise _error("page lines must be one list")
        lines = []
        for expected_index, raw_line in enumerate(raw_page["lines"]):
            if type(raw_line) is not dict or set(raw_line) != {
                "bbox",
                "source_line_index",
                "source_text",
                "vietocr_text",
            }:
                raise _error("purchased-debt matcher line fields drifted")
            if raw_line["source_line_index"] != expected_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if type(raw_line["vietocr_text"]) is not str:
                raise _error("fresh VietOCR text must be one exact string")
            bbox = _bbox(raw_line["bbox"])
            lines.append(
                {
                    "bbox": bbox,
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["vietocr_text"]),
                    "page_sequence": sequence,
                    "source_line_index": expected_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": sequence,
                "primary_numeric_authority": raw_page["primary_numeric_authority"],
            }
        )
        previous_page = sequence
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
    value_tokens = value.split()
    expected_tokens = expected.split()
    if expected in value:
        return True
    minimum = max(1, len(expected_tokens) - 1)
    maximum = min(len(value_tokens), len(expected_tokens) + 1)
    for width in range(minimum, maximum + 1):
        for start in range(0, len(value_tokens) - width + 1):
            surface = " ".join(value_tokens[start : start + width])
            if _edit_distance(surface, expected) <= allowance:
                return True
    return False


def _record(line: Mapping[str, Any], kind: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "match_kind": kind,
        "normalized_surface": line["normalized_text"],
        "page_sequence": line["page_sequence"],
        "source_line_index": line["source_line_index"],
        "surface": line["vietocr_text"],
    }


def _is_strong_owner(text: str) -> bool:
    tokens = text.split()
    return (
        3 <= len(tokens) <= 7
        and not any(
            phrase in text
            for phrase in (
                "bien dong",
                "chat luong",
                "chi phi",
                "du phong",
                "va hoat dong",
            )
        )
        and _near_phrase(text, "hoat dong mua no")
    )


def _is_weak_mention(text: str) -> bool:
    return text == "mua no"


def _role(text: str) -> str | None:
    if _near_phrase(text, "mua no bang vnd"):
        return "purchase_vnd"
    if _near_phrase(text, "mua no bang ngoai te", allowance=3):
        return "purchase_fx"
    if _near_phrase(text, "no goc da mua"):
        return "principal"
    if _near_phrase(text, "lai cua khoan no da mua", allowance=3):
        return "interest"
    if _near_phrase(text, "du phong rui ro") and len(text.split()) <= 8:
        return "provision"
    if "phan tich chat luong" in text and "mua no" in text:
        return "quality_branch"
    if ("thay doi du phong" in text or "bien dong du phong" in text) and "mua no" in text:
        return "provision_movement_branch"
    return None


def _is_next_family(text: str) -> bool:
    return _near_phrase(text, "chung khoan dau tu", allowance=2) and not any(
        token in text for token in ("du phong", "rui ro", "phan tich")
    )


def _is_period(text: str) -> bool:
    return (
        bool(_DATE.search(text))
        or bool(re.fullmatch(r"ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9]", text))
        or bool(re.fullmatch(r"nam\s+20[0-9]{2}", text))
    )


def _is_unit(text: str) -> bool:
    return text in {"trieu dong", "trieu vnd"}


def _is_numeric(text: str) -> bool:
    compact = text.strip().replace(" ", "")
    return bool(_NUMBER.fullmatch(compact)) or compact in {"-", "–", "—"}


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [canonical_clone_v1(line) for page in pages for line in page["lines"]]


def _anchor_combination(anchors: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ordered_roles = [role for role in _CORE_ROLES if role in anchors]
    pair_candidates = [list(pair) for pair in itertools.combinations(ordered_roles, 2)]
    selected = pair_candidates[0] if pair_candidates else None
    return {
        "larger_combination_used": False,
        "pair_candidates": pair_candidates,
        "pair_search_exhausted_first": True,
        "selected_minimal_pair": selected,
    }


def _candidate_region(
    lines: Sequence[Mapping[str, Any]], owner_index: int, *, strong_owner: bool
) -> dict[str, Any]:
    owner = lines[owner_index]
    end = min(len(lines), owner_index + _MAX_REGION_LINES)
    boundary_line: Mapping[str, Any] | None = None
    for line in lines[owner_index + 1 : end]:
        if line["page_sequence"] > owner["page_sequence"] + _MAX_REGION_PAGES - 1:
            end = line["global_ordinal"]
            break
        if _is_next_family(line["normalized_text"]):
            boundary_line = line
            end = line["global_ordinal"]
            break
    window = [line for line in lines[owner_index + 1 :] if line["global_ordinal"] < end]
    anchors: dict[str, dict[str, Any]] = {"owner": _record(owner, "FAMILY_OWNER")}
    optional_branches: list[dict[str, Any]] = []
    purchase_seen = False
    principal_seen = False
    for line in window:
        role = _role(line["normalized_text"])
        if role == "purchase_vnd" and "purchase_vnd" not in anchors:
            anchors[role] = _record(line, role.upper())
            purchase_seen = True
        elif role == "purchase_fx" and purchase_seen and "purchase_fx" not in anchors:
            anchors[role] = _record(line, role.upper())
        elif role == "provision" and purchase_seen and "provision" not in anchors:
            anchors[role] = _record(line, role.upper())
        elif role == "principal" and purchase_seen and "principal" not in anchors:
            anchors[role] = _record(line, role.upper())
            principal_seen = True
        elif role == "interest" and principal_seen and "interest" not in anchors:
            anchors[role] = _record(line, role.upper())
        elif role in {"quality_branch", "provision_movement_branch"}:
            optional_branches.append(_record(line, role.upper()))
    period_lines = [
        _record(line, "PERIOD_AXIS") for line in window if _is_period(line["normalized_text"])
    ]
    unit_lines = [
        _record(line, "UNIT_AXIS") for line in window if _is_unit(line["normalized_text"])
    ]
    numeric_count = sum(_is_numeric(line["normalized_text"]) for line in window)
    reasons = []
    if not strong_owner:
        reasons.append("BARE_MUA_NO_MENTION_NOT_FAMILY_OWNER")
    for role in _CORE_ROLES[1:]:
        if role not in anchors:
            reasons.append(f"MISSING_{role.upper()}_ANCHOR")
    if len(period_lines) < 2:
        reasons.append("TWO_PERIOD_AXIS_NOT_RESOLVED")
    if len(unit_lines) < 2:
        reasons.append("TWO_UNIT_AXIS_NOT_RESOLVED")
    if boundary_line is None:
        reasons.append("NEXT_FAMILY_BOUNDARY_NOT_RESOLVED")
    if numeric_count < 6:
        reasons.append("NUMERIC_SURFACE_TOO_SPARSE_FOR_TABLE")
    complete = not reasons
    last_anchor = anchors.get("interest", anchors.get("principal", anchors["owner"]))
    material = {
        "anchor_combination": _anchor_combination(anchors),
        "anchors": anchors,
        "boundary": {
            "first_item": canonical_clone_v1(anchors["owner"]),
            "last_schema_item": canonical_clone_v1(last_anchor),
            "next_family": None
            if boundary_line is None
            else _record(boundary_line, "NEXT_TM_FAMILY"),
        },
        "layout": "ACCOUNTING_ROWS_X_PERIOD_COLUMNS_WITH_OPTIONAL_TRAILING_BRANCHES",
        "numeric_surface_count": numeric_count,
        "optional_branches": optional_branches,
        "page_span": [
            owner["page_sequence"],
            window[-1]["page_sequence"] if window else owner["page_sequence"],
        ],
        "period_axes": period_lines,
        "source_order": [
            role for role, _ in sorted(anchors.items(), key=lambda item: item[1]["global_ordinal"])
        ],
        "unit_axes": unit_lines,
        "unresolved_reasons": reasons,
    }
    return {
        **material,
        "region_id": "pdvgv1:region:" + canonical_json_sha256_v1(material),
        "state": "COMPLETE_PURCHASED_DEBT_REGION" if complete else "NEAR_PURCHASED_DEBT_REGION",
    }


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": len(regions),
        "mapping_verified_count": 0,
        "near_region_count": len(near),
        "optional_branch_count": sum(len(region["optional_branches"]) for region in regions),
        "region_candidate_count": len(regions) + len(near),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("purchased-debt graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("purchased-debt graph identity or safety drifted")
    expected_metrics = _metrics(value["regions"], value["near_regions"])
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("purchased-debt graph metrics drifted")
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(value["regions"]) == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if not value["regions"]
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_uniqueness = {
        "complete_region_count": len(value["regions"]),
        "status": (
            "UNIQUE_FULL_MATCH"
            if len(value["regions"]) == 1
            else "NO_FULL_MATCH"
            if not value["regions"]
            else "MULTIPLE_FULL_MATCHES"
        ),
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("purchased-debt graph status or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "pdvgv1:document:" + canonical_json_sha256_v1(material):
        raise _error("purchased-debt graph identity drifted")
    return canonical_clone_v1(value)


def build_purchased_debt_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every purchased-debt-like region in one complete PDF."""

    checked_pages = _pages(pages)
    lines = _flatten(checked_pages)
    candidates: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        text = line["normalized_text"]
        if _is_strong_owner(text):
            candidates.append(_candidate_region(lines, index, strong_owner=True))
        elif _is_weak_mention(text):
            candidates.append(_candidate_region(lines, index, strong_owner=False))
    regions = [item for item in candidates if item["state"] == "COMPLETE_PURCHASED_DEBT_REGION"]
    near = [item for item in candidates if item["state"] == "NEAR_PURCHASED_DEBT_REGION"]
    status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(regions) == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if not regions
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(regions, near),
        "near_regions": near,
        "regions": regions,
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": (
                "UNIQUE_FULL_MATCH"
                if len(regions) == 1
                else "NO_FULL_MATCH"
                if not regions
                else "MULTIPLE_FULL_MATCHES"
            ),
        },
    }
    return _validate_result(
        {**material, "result_id": "pdvgv1:document:" + canonical_json_sha256_v1(material)}
    )


def validate_purchased_debt_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    """Exact-rebuild a document result from its complete fresh-VietOCR pages."""

    persisted = _validate_result(value)
    expected = build_purchased_debt_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, expected):
        raise _error("purchased-debt graph does not replay exactly")
    return persisted
