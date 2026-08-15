"""Bank-blind complete-PDF graph for the investment-securities family.

The live TM interval is ReportNormId 804 through 861, immediately before
ReportNormId 862 (other long-term investments).  The common core is one
available-for-sale (AFS) branch containing a debt parent and at least one
issuer child.  A held-to-maturity (HTM) branch, provision detail, credit-
quality view and VAMC branch are optional.  The source may omit the printed
family owner when the AFS core and the next-family boundary are unique.

Fresh VietOCR Transformer text is anchor evidence only.  Numeric values,
period/unit scope, DASH cells, gross/net equations and schema mapping require
an independent visible-PDF replay.  No bank, filename, page or note number is
a matching condition.
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
    "InvestmentSecuritiesVariantGraphV1Error",
    "build_investment_securities_variant_graph_document_v1",
    "validate_investment_securities_variant_graph_replay_v1",
]

FORMAT_VERSION = "INVESTMENT_SECURITIES_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "INVESTMENT_SECURITIES"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_INVESTMENT_SECURITIES_EXPLICIT_"
    "OR_IMPLICIT_OWNER_AFS_DEBT_ISSUER_OPTIONAL_HTM_PROVISION_QUALITY_VAMC_"
    "FIRST_LAST_NEXT_FAMILY_BOUNDARY_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "implicit_owner_requires_unique_afs_parent_issuer_pair_and_next_boundary": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_branch_can_be_added_to_core_without_equation_replay": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
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
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|(?:nam\s+20[0-9]{2})|"
    r"(?:so\s+(?:cuoi|dau)\s+ky)"
)
_MAX_REGION_PAGES = 3
_MAX_REGION_LINES = 360


class InvestmentSecuritiesVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed investment graph drifted."""


def _error(message: str) -> InvestmentSecuritiesVariantGraphV1Error:
    return InvestmentSecuritiesVariantGraphV1Error(message)


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
        raise _error("investment-securities matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    previous_page = 0
    global_ordinal = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("investment-securities matcher page fields drifted")
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
                raise _error("investment-securities matcher line fields drifted")
            if raw_line["source_line_index"] != expected_index:
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
    if expected in value:
        return True
    value_tokens = value.split()
    expected_tokens = expected.split()
    for width in range(
        max(1, len(expected_tokens) - 1), min(len(value_tokens), len(expected_tokens) + 1) + 1
    ):
        for start in range(0, len(value_tokens) - width + 1):
            if _edit_distance(" ".join(value_tokens[start : start + width]), expected) <= allowance:
                return True
    return False


def _strip_number(text: str) -> str:
    return re.sub(r"^(?:[0-9]+\s+)+", "", text).strip()


def _is_owner(text: str) -> bool:
    return _strip_number(text) == "chung khoan dau tu"


def _is_afs(text: str) -> bool:
    return len(text.split()) <= 12 and _near_phrase(
        text, "chung khoan dau tu san sang de ban", allowance=3
    )


def _is_htm(text: str) -> bool:
    return len(text.split()) <= 18 and (
        _near_phrase(text, "chung khoan dau tu giu den ngay dao han", allowance=3)
        or _near_phrase(text, "chung khoan dau tu nam giu den ngay dao han", allowance=3)
    )


def _is_next_family(text: str) -> bool:
    stripped = _strip_number(text)
    return len(stripped.split()) <= 9 and any(
        _near_phrase(stripped, phrase, allowance=2)
        for phrase in (
            "gop von dau tu dai han",
            "cac khoan dau tu dai han khac",
            "dau tu dai han khac",
        )
    )


def _issuer_role(text: str) -> str | None:
    if "chinh phu bao lanh" in text:
        return "government_guaranteed"
    if "chinh phu" in text or "chinh quyen dia phuong" in text:
        return "government"
    if "tctd" in text and ("phat hanh" in text or "trai phieu" in text or "chung chi" in text):
        return "other_credit_institution"
    if any(term in text for term in ("tckt trong nuoc", "to chuc kinh te trong nuoc")):
        return "domestic_economic_organization"
    if any(
        term in text for term in ("nuoc ngoai", "tckt nuoc ngoai", "to chuc kinh te nuoc ngoai")
    ):
        return "foreign_organization"
    return None


def _is_debt_parent(text: str) -> bool:
    return text == "chung khoan no"


def _is_equity_parent(text: str) -> bool:
    return text == "chung khoan von"


def _role(text: str, phase: str) -> str | None:
    if _is_htm(text):
        return "htm"
    if "phan tich chat luong" in text and "chung khoan" in text:
        return "quality"
    if _is_afs(text):
        return "afs"
    if "du phong" in text and "vamc" in text:
        return "vamc_provision"
    if "menh gia" in text and "vamc" in text:
        return "vamc_face_value"
    if phase == "trailing":
        return None
    if "du phong" in text and "chung khoan" in text and len(text.split()) <= 14:
        return "htm_provision" if phase == "htm" else "afs_provision"
    if _is_debt_parent(text):
        return "htm_debt" if phase == "htm" else "afs_debt"
    if _is_equity_parent(text):
        return "htm_equity" if phase == "htm" else "afs_equity"
    if "tai san tai chinh khac" in text:
        return "afs_other"
    issuer = _issuer_role(text)
    return None if issuer is None else f"{phase}_{issuer}"


def _is_period(text: str) -> bool:
    return bool(_DATE.search(text)) or text in {"30 06 2026", "31 12 2025"}


def _is_unit(text: str) -> bool:
    return text in {"trieu dong", "trieu vnd"}


def _is_numeric(text: str) -> bool:
    compact = text.strip().replace(" ", "")
    return bool(_NUMBER.fullmatch(compact)) or compact in {"-", "–", "—"}


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


def _flatten(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [canonical_clone_v1(line) for page in pages for line in page["lines"]]


def _has_aligned_numeric_follower(
    anchor: Mapping[str, Any], lines: Sequence[Mapping[str, Any]], end: int
) -> bool:
    for line in lines[anchor["global_ordinal"] + 1 : min(end, anchor["global_ordinal"] + 7)]:
        if line["page_sequence"] != anchor["page_sequence"]:
            break
        if (
            _is_numeric(line["normalized_text"])
            and line["bbox"][0] > anchor["bbox"][0]
            and abs(line["bbox"][1] - anchor["bbox"][1]) <= 85
        ):
            return True
    return False


def _anchor_combination(anchors: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    issuer_roles = sorted(
        (
            role
            for role in anchors
            if role.startswith("afs_")
            and role not in {"afs_debt", "afs_equity", "afs_other", "afs_provision"}
        ),
        key=lambda role: anchors[role]["global_ordinal"],
    )
    core = [role for role in ("owner", "afs", "afs_debt") if role in anchors]
    core.extend(issuer_roles[:1])
    pairs = [list(pair) for pair in itertools.combinations(core, 2)]
    preferred = (
        ["afs", "afs_debt"]
        if "afs" in anchors and "afs_debt" in anchors
        else ["afs", issuer_roles[0]]
        if "afs" in anchors and issuer_roles
        else pairs[0]
        if pairs
        else None
    )
    return {
        "larger_combination_used": False,
        "pair_candidates": pairs,
        "pair_search_exhausted_first": True,
        "selected_minimal_pair": preferred,
    }


def _candidate_region(
    lines: Sequence[Mapping[str, Any]], start_index: int, *, explicit_owner: bool
) -> dict[str, Any]:
    start = lines[start_index]
    end = min(len(lines), start_index + _MAX_REGION_LINES)
    boundary_line: Mapping[str, Any] | None = None
    for line in lines[start_index + 1 : end]:
        if line["page_sequence"] > start["page_sequence"] + _MAX_REGION_PAGES - 1:
            end = line["global_ordinal"]
            break
        if _is_next_family(line["normalized_text"]):
            boundary_line = line
            end = line["global_ordinal"]
            break
    window = [line for line in lines[start_index + 1 :] if line["global_ordinal"] < end]
    anchors: dict[str, dict[str, Any]] = {}
    if explicit_owner:
        anchors["owner"] = _record(start, "FAMILY_OWNER")
    else:
        anchors["afs"] = _record(start, "IMPLICIT_OWNER_AFS_FIRST_ITEM")
    optional: list[dict[str, Any]] = []
    phase = "afs"
    for line in window:
        role = _role(line["normalized_text"], phase)
        if role == "afs" and "afs" not in anchors:
            anchors[role] = _record(line, "AFS_BRANCH")
        elif role == "htm":
            phase = "htm"
            if "htm" not in anchors:
                anchors[role] = _record(line, "OPTIONAL_HTM_BRANCH")
                optional.append(canonical_clone_v1(anchors[role]))
        elif role in {
            "quality",
            "afs_provision",
            "htm_provision",
            "vamc_face_value",
            "vamc_provision",
        }:
            if role not in anchors:
                anchors[role] = _record(line, role.upper())
                optional.append(canonical_clone_v1(anchors[role]))
            if role == "quality":
                phase = "trailing"
        elif role is not None and role not in anchors:
            anchors[role] = _record(line, role.upper())
    period_lines = [
        _record(line, "PERIOD_AXIS") for line in window if _is_period(line["normalized_text"])
    ]
    unit_lines = [
        _record(line, "UNIT_AXIS") for line in window if _is_unit(line["normalized_text"])
    ]
    numeric_count = sum(_is_numeric(line["normalized_text"]) for line in window)
    issuer_roles = [
        role
        for role in anchors
        if role.startswith("afs_")
        and role not in {"afs_debt", "afs_equity", "afs_other", "afs_provision"}
    ]
    issuer_roles_with_values = [
        role for role in issuer_roles if _has_aligned_numeric_follower(anchors[role], lines, end)
    ]
    reasons = []
    if "afs" not in anchors:
        reasons.append("MISSING_AFS_ANCHOR")
    if len(issuer_roles_with_values) < 2:
        reasons.append("TWO_AFS_ISSUER_CHILDREN_NOT_RESOLVED")
    if len(period_lines) < 2:
        reasons.append("TWO_PERIOD_AXIS_NOT_RESOLVED")
    if boundary_line is None:
        reasons.append("NEXT_FAMILY_BOUNDARY_NOT_RESOLVED")
    if numeric_count < 4:
        reasons.append("NUMERIC_SURFACE_TOO_SPARSE_FOR_TABLE")
    complete = not reasons
    ordered = sorted(anchors.items(), key=lambda item: item[1]["global_ordinal"])
    last_anchor = ordered[-1][1]
    material = {
        "anchor_combination": _anchor_combination(anchors),
        "anchors": anchors,
        "boundary": {
            "first_item": canonical_clone_v1(
                anchors["owner"] if "owner" in anchors else anchors["afs"]
            ),
            "last_schema_anchor": canonical_clone_v1(last_anchor),
            "next_family": None
            if boundary_line is None
            else _record(boundary_line, "NEXT_TM_FAMILY"),
        },
        "layout": "ACCOUNTING_ROWS_X_PERIOD_COLUMNS_WITH_OPTIONAL_HTM_QUALITY_OR_VAMC_BRANCHES",
        "issuer_children_with_aligned_numeric_followers": issuer_roles_with_values,
        "numeric_surface_count": numeric_count,
        "optional_branches": optional,
        "owner_mode": "EXPLICIT_FAMILY_OWNER"
        if explicit_owner
        else "IMPLICIT_OWNER_UNIQUE_AFS_CORE",
        "page_span": [
            start["page_sequence"],
            window[-1]["page_sequence"] if window else start["page_sequence"],
        ],
        "period_axes": period_lines,
        "source_order": [role for role, _ in ordered],
        "unit_axes": unit_lines,
        "unresolved_reasons": reasons,
    }
    return {
        **material,
        "region_id": "isvgv1:region:" + canonical_json_sha256_v1(material),
        "state": "COMPLETE_INVESTMENT_SECURITIES_REGION"
        if complete
        else "NEAR_INVESTMENT_SECURITIES_REGION",
    }


def _metrics(
    regions: Sequence[Mapping[str, Any]], near: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": len(regions),
        "explicit_owner_region_count": sum(
            region["owner_mode"] == "EXPLICIT_FAMILY_OWNER" for region in regions
        ),
        "implicit_owner_region_count": sum(
            region["owner_mode"] == "IMPLICIT_OWNER_UNIQUE_AFS_CORE" for region in regions
        ),
        "mapping_verified_count": 0,
        "near_region_count": len(near),
        "optional_branch_count": sum(len(region["optional_branches"]) for region in regions),
        "region_candidate_count": len(regions) + len(near),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-securities graph result fields drifted")
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
        raise _error("investment-securities graph identity, safety or metrics drifted")
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(value["regions"]) == 1
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if not value["regions"]
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    )
    expected_uniqueness = {
        "complete_region_count": len(value["regions"]),
        "status": "UNIQUE_FULL_MATCH"
        if len(value["regions"]) == 1
        else "NO_FULL_MATCH"
        if not value["regions"]
        else "MULTIPLE_FULL_MATCHES",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_uniqueness
    ):
        raise _error("investment-securities graph status or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "isvgv1:document:" + canonical_json_sha256_v1(material):
        raise _error("investment-securities graph identity drifted")
    return canonical_clone_v1(value)


def build_investment_securities_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    """Enumerate every investment-securities-like region in one complete PDF."""

    lines = _flatten(_pages(pages))
    owner_indexes = [
        index for index, line in enumerate(lines) if _is_owner(line["normalized_text"])
    ]
    candidates = [_candidate_region(lines, index, explicit_owner=True) for index in owner_indexes]
    if not any(item["state"] == "COMPLETE_INVESTMENT_SECURITIES_REGION" for item in candidates):
        candidates.extend(
            _candidate_region(lines, index, explicit_owner=False)
            for index, line in enumerate(lines)
            if _is_afs(line["normalized_text"])
        )
    regions = [
        item for item in candidates if item["state"] == "COMPLETE_INVESTMENT_SECURITIES_REGION"
    ]
    near = [item for item in candidates if item["state"] == "NEAR_INVESTMENT_SECURITIES_REGION"]
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
        else "UNRESOLVED_NO_COMPLETE_REGION"
        if not regions
        else "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS",
        "uniqueness": {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH"
            if len(regions) == 1
            else "NO_FULL_MATCH"
            if not regions
            else "MULTIPLE_FULL_MATCHES",
        },
    }
    return _validate_result(
        {**material, "result_id": "isvgv1:document:" + canonical_json_sha256_v1(material)}
    )


def validate_investment_securities_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Exact-rebuild a document result from its complete fresh-VietOCR pages."""

    persisted = _validate_result(value)
    expected = build_investment_securities_variant_graph_document_v1(pages)
    if not same_typed_json_v1(persisted, expected):
        raise _error("investment-securities graph does not replay exactly")
    return persisted
