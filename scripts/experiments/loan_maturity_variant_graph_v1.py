"""Variant-aware, bank-blind graph matcher for loan-maturity disclosures.

The invariant is intentionally small::

    customer-loan owner
      -> maturity/time branch
      -> optional ``Dư nợ cho vay`` presentation header
      -> SHORT, MEDIUM, LONG in order
      -> core total and/or optional margin/advance child and grand total

Names, local headers, lane layouts, total presentation, and owner/unit/period
inheritance may vary.  The matcher therefore models those differences as typed
variants instead of routing by bank, filename, note number, or page number.

Document pages are used only to prove that the complete graph occurrence is
unique and to resolve an immediately preceding owner/unit context.  Every
semantic line must carry a VietOCR Transformer proposal.  Qwen3.5 challenger
text may be retained as diagnostic input, but it never participates in a
semantic match: the sealed 27B trial was not reliable enough for authority.
Legacy OCR transcripts never enter label matching.  Numeric values are
authoritative only when the caller supplies exact source text for the same
bound line; semantic-reader text alone can establish structure but never
numeric truth.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    build_accounting_variant_region_scan_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanMaturityVariantGraphV1Error",
    "build_loan_maturity_region_scan_v1",
    "build_loan_maturity_variant_graph_v1",
    "scan_loan_maturity_variant_graph_document_v1",
    "validate_loan_maturity_variant_graph_replay_v1",
]


FORMAT_VERSION = "LOAN_MATURITY_VARIANT_GRAPH_V1"
CLAIM_BOUNDARY = (
    "BANK_BLIND_DOCUMENT_UNIQUE_LOAN_MATURITY_STRUCTURE_AND_TYPED_VARIANTS_ONLY_"
    "TRANSFORMER_TEXT_IS_SEMANTIC_PROPOSAL_SOURCE_TEXT_REQUIRED_FOR_NUMERIC_"
    "AUTHORITY_NO_SCHEMA_MAPPING_VERIFICATION_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)

_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
_MAX_BRANCH_TO_LONG_LINE_SPAN = 32
_MAX_ROLE_GAP = 12
_MAX_AFTER_LONG_LINE_SPAN = 20
_ROLE_SCHEMA_IDS = {"SHORT_TERM": 753, "MEDIUM_TERM": 754, "LONG_TERM": 755}
_ROLE_ALIASES = {
    "SHORT_TERM": ("no ngan han", "cho vay ngan han"),
    "MEDIUM_TERM": ("no trung han", "cho vay trung han"),
    "LONG_TERM": ("no dai han", "cho vay dai han"),
}
_FAMILY_ENGINE_SPEC = {
    "branch_core_phrases": ["phân tích", "dư nợ"],
    "branch_variants": [
        {"anchor_phrase": "thời gian cho vay ban đầu", "variant_id": "INITIAL_TERM_WORDING"},
        {"anchor_phrase": "thời gian cho vay gốc", "variant_id": "ORIGINAL_TERM_WORDING"},
        {"anchor_phrase": "thời hạn gốc", "variant_id": "ORIGINAL_TERM_WORDING"},
        {"anchor_phrase": "thời gian đáo hạn", "variant_id": "MATURITY_TIME_WORDING"},
        {"anchor_phrase": "thời hạn vay", "variant_id": "TERM_WORDING"},
        {"anchor_phrase": "thời gian", "variant_id": "TIME_WORDING"},
        {"anchor_phrase": "thời hạn", "variant_id": "TERM_WORDING"},
        {"anchor_phrase": "kỳ hạn", "variant_id": "TENOR_WORDING"},
    ],
    "family_id": "LOAN_MATURITY_BUCKETS",
    "format_version": "ACCOUNTING_VARIANT_FAMILY_SPEC_V1",
    "limits": {
        "max_branch_to_last_child_line_span": _MAX_BRANCH_TO_LONG_LINE_SPAN,
        "max_child_gap": _MAX_ROLE_GAP,
        "min_numeric_followers_per_child": 2,
    },
    "optional_intermediate_aliases": ["Dư nợ cho vay", "Dư nợ cho vay khách hàng"],
    "ordered_children": [
        {"aliases": list(_ROLE_ALIASES["SHORT_TERM"]), "role": "SHORT_TERM"},
        {"aliases": list(_ROLE_ALIASES["MEDIUM_TERM"]), "role": "MEDIUM_TERM"},
        {"aliases": list(_ROLE_ALIASES["LONG_TERM"]), "role": "LONG_TERM"},
    ],
    "owner_aliases": [
        "Cho vay khách hàng",
        "Dư nợ cho vay khách hàng",
        "Các khoản cho vay khách hàng",
    ],
}
_SAFETY = {
    "bank_filename_note_or_page_used_for_inference": False,
    "document_pages_used_for_unique_graph_and_inherited_context_only": True,
    "fresh_semantic_page_required_for_role_acceptance": True,
    "legacy_canary_semantic_authority_used": False,
    "legacy_ocr_transcript_used_for_semantic_matching": False,
    "mapping_authority": False,
    "numeric_authority_requires_bound_source_text": True,
    "optional_rows_silently_discarded": False,
    "percentage_lanes_silently_discarded": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "qwen35_challenger_semantic_authority_used": False,
    "schema_ids_are_candidates_not_verified_mappings": True,
    "transformer_numeric_text_used_as_source_truth": False,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "document_candidate_count",
    "format_version",
    "graph_id",
    "metrics",
    "result",
    "safety",
    "status",
    "unresolved_reasons",
}
_NUMBER = re.compile(r"^[()]*[+-]?[0-9][0-9., ]*%?[()]*$")
_FULL_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_DAY_MONTH = re.compile(r"\bngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\b")
_YEAR = re.compile(r"\bnam\s+(\d{4})\b")


class LoanMaturityVariantGraphV1Error(ValueError):
    """The generic graph input or deterministic replay drifted."""


def _error(message: str) -> LoanMaturityVariantGraphV1Error:
    return LoanMaturityVariantGraphV1Error(message)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", text).split())


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    left_index = 0
    right_index = 0
    differences = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            left_index += 1
            right_index += 1
        else:
            differences += 1
            right_index += 1
            if differences > 1:
                return False
    return True


def _semantic_candidates(line: Mapping[str, Any]) -> list[tuple[str, str]]:
    # Qwen is deliberately excluded.  Its value remains in the bound record so
    # a diagnostic trial can be audited without silently changing the matcher.
    return [("VIETOCR_TRANSFORMER", line["vietocr_text"])]


def _semantic_match(line: Mapping[str, Any], predicate: Any) -> tuple[str, str] | None:
    for source, text in _semantic_candidates(line):
        if predicate(text):
            return source, text
    return None


def _owner_heading(text: str) -> bool:
    normalized = _normalize(text)
    normalized = re.sub(r"^(?:[0-9]+\s+)+", "", normalized)
    aliases = (
        "cho vay khach hang",
        "du no cho vay khach hang",
        "cac khoan cho vay khach hang",
    )
    return any(
        normalized == alias or _edit_distance_at_most_one(normalized, alias) for alias in aliases
    )


def _intermediate_header(text: str) -> bool:
    return _normalize(text) in {"du no cho vay", "du no cho vay khach hang"}


def _margin_text(text: str) -> bool:
    normalized = _normalize(text)
    return "margin" in normalized or "ky quy" in normalized or "ung truoc" in normalized


def _new_numbered_section(text: str) -> bool:
    """Recognize a following numbered disclosure heading, not a table cell."""

    normalized = _normalize(text)
    return not _number_like(text) and re.match(r"^[0-9]{1,3}\s+[a-z]", normalized) is not None


def _number_like(text: str) -> bool:
    compact = text.strip().replace("\u00a0", " ").replace("\u202f", " ")
    return bool(compact and _NUMBER.fullmatch(compact) and any(char.isdigit() for char in compact))


def _money_integer(text: str) -> int | None:
    compact = text.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    if (
        compact.endswith("%")
        or not compact
        or not all(char.isdigit() or char in ".," for char in compact)
    ):
        return None
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        return None
    value = int(digits)
    return -value if negative else value


def _percentage(text: str) -> Decimal | None:
    compact = text.strip().replace(" ", "").rstrip("%").replace(",", ".")
    try:
        value = Decimal(compact)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _exact_page(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"lines", "page_sequence"}:
        raise _error(f"{label} fields drifted")
    if type(value["page_sequence"]) is not int or value["page_sequence"] <= 0:
        raise _error(f"{label} page sequence must be one positive integer")
    if type(value["lines"]) is not list:
        raise _error(f"{label} lines must be one list")
    lines: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(value["lines"]):
        if type(raw) is not dict or set(raw) != {
            "qwen35_challenger_text",
            "source_line_index",
            "vietocr_text",
        }:
            raise _error(f"{label} semantic line fields drifted")
        if (
            type(raw["source_line_index"]) is not int
            or raw["source_line_index"] != ordinal
            or type(raw["vietocr_text"]) is not str
            or (
                raw["qwen35_challenger_text"] is not None
                and type(raw["qwen35_challenger_text"]) is not str
            )
        ):
            raise _error(f"{label} semantic line identity/text drifted")
        lines.append(canonical_clone_v1(raw))
    return {"lines": lines, "page_sequence": value["page_sequence"]}


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


def _semantic_page(value: Any, *, allow_empty: bool = False) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "lines",
        "page_sequence",
        "primary_numeric_authority",
    }:
        raise _error("semantic page fields drifted")
    if type(value["page_sequence"]) is not int or value["page_sequence"] <= 0:
        raise _error("semantic page sequence drifted")
    if type(value["primary_numeric_authority"]) is not bool:
        raise _error("semantic page numeric authority must be one exact bool")
    if type(value["lines"]) is not list or (not allow_empty and not value["lines"]):
        raise _error("semantic page line denominator drifted")
    lines: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(value["lines"]):
        if type(raw) is not dict or set(raw) != {
            "bbox",
            "qwen35_challenger_text",
            "source_line_index",
            "source_text",
            "vietocr_text",
        }:
            raise _error("semantic line fields drifted")
        if (
            type(raw["source_line_index"]) is not int
            or raw["source_line_index"] != ordinal
            or type(raw["vietocr_text"]) is not str
            or (
                raw["qwen35_challenger_text"] is not None
                and type(raw["qwen35_challenger_text"]) is not str
            )
            or (raw["source_text"] is not None and type(raw["source_text"]) is not str)
        ):
            raise _error("semantic line identity/text drifted")
        lines.append(
            {
                "bbox": _bbox(raw["bbox"], f"semantic line {ordinal}"),
                "qwen35_challenger_text": raw["qwen35_challenger_text"],
                "source_line_index": ordinal,
                "source_text": raw["source_text"],
                "vietocr_text": raw["vietocr_text"],
            }
        )
    return {
        "page_sequence": value["page_sequence"],
        "primary_numeric_authority": value["primary_numeric_authority"],
        "lines": lines,
    }


def _region_scan_from_exact_pages(pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    engine_pages = [
        {
            "page_sequence": page["page_sequence"],
            "lines": [
                {
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
        }
        for page in pages
    ]
    return build_accounting_variant_region_scan_v1(engine_pages, _FAMILY_ENGINE_SPEC)


def build_loan_maturity_region_scan_v1(
    document_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Enumerate all complete and near maturity regions in one complete PDF."""

    if isinstance(document_pages, (str, bytes, bytearray)) or not document_pages:
        raise _error("document pages must be one non-empty sequence")
    pages = [
        _exact_page(page, f"maturity region scan page {index}")
        for index, page in enumerate(document_pages)
    ]
    sequences = [page["page_sequence"] for page in pages]
    if sequences != sorted(sequences) or len(set(sequences)) != len(sequences):
        raise _error("maturity region scan pages must be unique and ordered")
    return _region_scan_from_exact_pages(pages)


def _document_candidates(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    scan = _region_scan_from_exact_pages(pages)
    candidates: list[dict[str, Any]] = []
    for region in scan["regions"]:
        # Missing owner is diagnosed later with the richer source/page context.
        # Every other engine reason vetoes a complete ordered anchor region.
        if any(reason != "OWNER_CONTEXT_NOT_RESOLVED" for reason in region["unresolved_reasons"]):
            continue
        candidates.append(
            {
                "branch_source_line_index": region["branch_source_line_index"],
                "branch_match": {
                    **region["branch_match"],
                    "semantic_source": "VIETOCR_TRANSFORMER",
                },
                "page_sequence": region["page_sequence"],
                "role_match_records": [
                    {
                        "kind": record["match_kind"],
                        "role": record["role"],
                        "semantic_source": "VIETOCR_TRANSFORMER",
                        "surface": record["surface"],
                    }
                    for record in region["child_match_records"]
                ],
                "role_source_line_indices": region["child_source_line_indices"],
            }
        )
    return candidates


def _unit_kind(text: str) -> str | None:
    normalized = _normalize(text)
    if "%" in normalized:
        return "PERCENT"
    if ("trieu" in normalized or "triu" in normalized) and (
        "dong" in normalized or "vnd" in normalized
    ):
        return "MONEY"
    return None


def _center_x(line: Mapping[str, Any]) -> int:
    return line["bbox"][0] + line["bbox"][2]


def _periods(header: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    full: list[dict[str, Any]] = []
    partial: list[tuple[Mapping[str, Any], int, int]] = []
    years: list[tuple[Mapping[str, Any], int]] = []
    relative: list[dict[str, Any]] = []
    for line in header:
        text = line["vietocr_text"]
        normalized = _normalize(text)
        match = _FULL_DATE.search(text)
        if match is not None:
            day, month, year = (int(item) for item in match.groups())
            full.append(
                {
                    "evidence_source_line_indices": [line["source_line_index"]],
                    "period": f"{day:02d}/{month:02d}/{year:04d}",
                    "x_center_x2": _center_x(line),
                }
            )
            continue
        match = _DAY_MONTH.search(normalized)
        if match is not None:
            partial.append((line, int(match.group(1)), int(match.group(2))))
            continue
        match = _YEAR.search(normalized)
        if match is not None:
            years.append((line, int(match.group(1))))
            continue
        if normalized == "so cuoi ky":
            relative.append(
                {
                    "evidence_source_line_indices": [line["source_line_index"]],
                    "period": "CURRENT_PERIOD_END",
                    "x_center_x2": _center_x(line),
                }
            )
        elif normalized == "so dau ky":
            relative.append(
                {
                    "evidence_source_line_indices": [line["source_line_index"]],
                    "period": "COMPARATIVE_PERIOD_START",
                    "x_center_x2": _center_x(line),
                }
            )
    if len(full) == 2:
        return sorted(full, key=lambda item: item["x_center_x2"]), "LOCAL_EXACT_DATES"
    if len(partial) == 2 and len(years) == 2:
        combined: list[dict[str, Any]] = []
        remaining = list(years)
        for line, day, month in sorted(partial, key=lambda item: _center_x(item[0])):
            year_line, year = min(
                remaining, key=lambda item: abs(_center_x(item[0]) - _center_x(line))
            )
            remaining.remove((year_line, year))
            combined.append(
                {
                    "evidence_source_line_indices": [
                        line["source_line_index"],
                        year_line["source_line_index"],
                    ],
                    "period": f"{day:02d}/{month:02d}/{year:04d}",
                    "x_center_x2": _center_x(line),
                }
            )
        return sorted(combined, key=lambda item: item["x_center_x2"]), "LOCAL_SPLIT_DATES"
    if len(relative) == 2:
        return sorted(relative, key=lambda item: item["x_center_x2"]), "LOCAL_RELATIVE_PERIOD_ROLES"
    return [], "UNRESOLVED"


def _inherited_unit(pages: Sequence[Mapping[str, Any]], target_page: int) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        if page["page_sequence"] >= target_page:
            continue
        for line_index, line in enumerate(page["lines"]):
            matched = _semantic_match(
                line,
                lambda text: (
                    ("trieu" in _normalize(text) or "triu" in _normalize(text))
                    and ("vnd" in _normalize(text) or "dong" in _normalize(text))
                    and ("don vi" in _normalize(text) or _normalize(text).startswith("don v "))
                ),
            )
            if matched is None:
                continue
            semantic_source, text = matched
            normalized = _normalize(text)
            if (
                ("trieu" in normalized or "triu" in normalized)
                and ("vnd" in normalized or "dong" in normalized)
                and ("don vi" in normalized or normalized.startswith("don v "))
            ):
                candidates.append(
                    {
                        "page_sequence": page["page_sequence"],
                        "semantic_source": semantic_source,
                        "source_line_index": line_index,
                        "surface": text,
                    }
                )
    return candidates[-1] if candidates else None


def _line_value(line: Mapping[str, Any], primary: bool) -> tuple[str, bool]:
    source = line["source_text"]
    if primary and source is not None and _number_like(source):
        return source, True
    return line["vietocr_text"], False


def _vector(
    lines: Sequence[Mapping[str, Any]], lane_types: Sequence[str], primary: bool
) -> list[dict[str, Any]] | None:
    numeric = [line for line in lines if _number_like(line["vietocr_text"])]
    if len(numeric) < len(lane_types):
        return None
    result: list[dict[str, Any]] = []
    for lane_index, (line, lane_type) in enumerate(zip(numeric, lane_types, strict=False)):
        if lane_index == len(lane_types):
            break
        surface, authoritative = _line_value(line, primary)
        result.append(
            {
                "lane_index": lane_index,
                "lane_type": lane_type,
                "numeric_source_authoritative": authoritative,
                "source_line_index": line["source_line_index"],
                "surface": surface,
            }
        )
    return result if len(result) == len(lane_types) else None


def _money_values(vector: Sequence[Mapping[str, Any]]) -> list[int] | None:
    result: list[int] = []
    for item in vector:
        if item["lane_type"] != "MONEY":
            continue
        if item["numeric_source_authoritative"] is not True:
            return None
        parsed = _money_integer(item["surface"])
        if parsed is None:
            return None
        result.append(parsed)
    return result


def _percentage_values(vector: Sequence[Mapping[str, Any]]) -> list[Decimal] | None:
    result: list[Decimal] = []
    for item in vector:
        if item["lane_type"] != "PERCENT":
            continue
        if item["numeric_source_authoritative"] is not True:
            return None
        parsed = _percentage(item["surface"])
        if parsed is None:
            return None
        result.append(parsed)
    return result


def _qwen_source_count(value: Any) -> int:
    if type(value) is dict:
        return (value.get("semantic_source") == "QWEN3_5_27B_GPTQ_INT4_CHALLENGER") + sum(
            _qwen_source_count(item) for item in value.values()
        )
    if type(value) is list:
        return sum(_qwen_source_count(item) for item in value)
    return 0


def _build_result(
    pages: Sequence[Mapping[str, Any]], semantic_page: Mapping[str, Any]
) -> dict[str, Any]:
    target = semantic_page["page_sequence"]
    merged_pages = [
        {
            "page_sequence": page["page_sequence"],
            "lines": (
                [
                    {
                        "qwen35_challenger_text": line["qwen35_challenger_text"],
                        "source_line_index": line["source_line_index"],
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in semantic_page["lines"]
                ]
                if page["page_sequence"] == target
                else canonical_clone_v1(page["lines"])
            ),
        }
        for page in pages
    ]
    candidates = _document_candidates(merged_pages)
    reasons: list[str] = []
    if len(candidates) != 1:
        reasons.append("DOCUMENT_COMPLETE_GRAPH_NOT_UNIQUE")
    if not candidates or candidates[0]["page_sequence"] != target:
        reasons.append("FRESH_SEMANTIC_PAGE_IS_NOT_UNIQUE_DOCUMENT_GRAPH")
    if reasons:
        return {
            "candidate_count": len(candidates),
            "graph": None,
            "status": "UNRESOLVED",
            "unresolved_reasons": sorted(set(reasons)),
        }

    candidate = candidates[0]
    lines = semantic_page["lines"]
    branch_index = candidate["branch_source_line_index"]
    role_indices = candidate["role_source_line_indices"]

    local_owners = [
        (line["source_line_index"], match)
        for line in lines[:branch_index]
        if (match := _semantic_match(line, _owner_heading)) is not None
    ]
    if local_owners:
        owner_index, owner_match = local_owners[-1]
        owner = {
            "mode": "SAME_PAGE_NEAREST_PRECEDING",
            "page_sequence": target,
            "semantic_source": owner_match[0],
            "source_line_index": owner_index,
            "surface": owner_match[1],
        }
    else:
        previous = next(
            (page for page in pages if page["page_sequence"] == target - 1),
            None,
        )
        previous_owners = (
            [
                (index, match)
                for index, line in enumerate(previous["lines"])
                if (match := _semantic_match(line, _owner_heading)) is not None
            ]
            if previous is not None
            else []
        )
        previous_owner_index, previous_owner_match = (
            previous_owners[-1] if previous_owners else (None, None)
        )
        owner = (
            {
                "mode": "IMMEDIATE_PREVIOUS_PAGE",
                "page_sequence": target - 1,
                "semantic_source": previous_owner_match[0],
                "source_line_index": previous_owner_index,
                "surface": previous_owner_match[1],
            }
            if previous_owners
            else None
        )
    if owner is None:
        reasons.append("CUSTOMER_LOAN_OWNER_NOT_RESOLVED")

    header = lines[branch_index + 1 : role_indices[0]]
    local_units: list[dict[str, Any]] = []
    for line in header:
        match = _semantic_match(line, lambda text: _unit_kind(text) is not None)
        if match is None:
            continue
        source, surface = match
        kind = _unit_kind(surface)
        assert kind is not None
        local_units.append(
            {
                "kind": kind,
                "semantic_source": source,
                "source_line_index": line["source_line_index"],
                "x_center_x2": _center_x(line),
            }
        )
    local_units.sort(key=lambda item: item["x_center_x2"])
    lane_types = [item["kind"] for item in local_units]

    row_numeric_counts = []
    for row_ordinal, role_index in enumerate(role_indices):
        stop = role_indices[row_ordinal + 1] if row_ordinal + 1 < len(role_indices) else len(lines)
        row_numeric_counts.append(
            sum(_number_like(line["vietocr_text"]) for line in lines[role_index + 1 : stop])
        )
    inferred_lane_count = min(row_numeric_counts)
    if not lane_types and inferred_lane_count == 2:
        lane_types = ["MONEY", "MONEY"]
    if lane_types not in (["MONEY", "MONEY"], ["MONEY", "PERCENT", "MONEY", "PERCENT"]):
        reasons.append("SUPPORTED_TYPED_LANE_LAYOUT_NOT_RESOLVED")

    if local_units:
        unit_scope: dict[str, Any] = {
            "mode": "LOCAL_PER_LANE",
            "lane_types": lane_types,
            "source_line_indices": [item["source_line_index"] for item in local_units],
        }
    else:
        inherited = _inherited_unit(pages, target)
        unit_scope = (
            {
                "mode": "INHERITED_NEAREST_PRECEDING_DOCUMENT_UNIT",
                "lane_types": lane_types,
                **inherited,
            }
            if inherited is not None
            else {"mode": "UNRESOLVED", "lane_types": lane_types}
        )
        if inherited is None:
            reasons.append("UNIT_SCOPE_NOT_RESOLVED")

    periods, period_mode = _periods(header)
    if not periods:
        reasons.append("PERIOD_AXIS_NOT_RESOLVED")

    rows: list[dict[str, Any]] = []
    for row_ordinal, (role, role_index, match_record) in enumerate(
        zip(_ROLES, role_indices, candidate["role_match_records"], strict=True)
    ):
        stop = role_indices[row_ordinal + 1] if row_ordinal + 1 < len(role_indices) else len(lines)
        vector = _vector(
            lines[role_index + 1 : stop], lane_types, semantic_page["primary_numeric_authority"]
        )
        if vector is None:
            reasons.append(f"{role}_VALUE_LANES_NOT_RESOLVED")
            vector = []
        rows.append(
            {
                "label_surface": match_record["surface"],
                "match_kind": match_record["kind"],
                "qwen35_challenger_text": lines[role_index]["qwen35_challenger_text"],
                "report_norm_id_candidate": _ROLE_SCHEMA_IDS[role],
                "role": role,
                "semantic_source": match_record["semantic_source"],
                "source_line_index": role_index,
                "vietocr_text": lines[role_index]["vietocr_text"],
                "values": vector,
            }
        )

    long_index = role_indices[-1]
    long_vector = rows[-1]["values"]
    after_start = max((item["source_line_index"] for item in long_vector), default=long_index) + 1
    after = lines[after_start : after_start + _MAX_AFTER_LONG_LINE_SPAN]
    section_boundary = next(
        (index for index, line in enumerate(after) if _new_numbered_section(line["vietocr_text"])),
        None,
    )
    if section_boundary is not None:
        after = after[:section_boundary]
    margin_offset = next(
        (
            index
            for index, line in enumerate(after)
            if _semantic_match(line, _margin_text) is not None
        ),
        None,
    )
    optional_margin: dict[str, Any] | None = None
    core_vector: list[dict[str, Any]] | None = None
    grand_vector: list[dict[str, Any]] | None = None
    if margin_offset is None:
        core_vector = _vector(after, lane_types, semantic_page["primary_numeric_authority"])
        total_variant = "CORE_TOTAL_ONLY"
    else:
        before_margin = after[:margin_offset]
        core_vector = _vector(before_margin, lane_types, semantic_page["primary_numeric_authority"])
        margin_label_end = margin_offset + 1
        while margin_label_end < len(after) and not _number_like(
            after[margin_label_end]["vietocr_text"]
        ):
            margin_label_end += 1
        margin_and_total = after[margin_label_end:]
        margin_vector = _vector(
            margin_and_total,
            lane_types,
            semantic_page["primary_numeric_authority"],
        )
        numeric_lines = [line for line in margin_and_total if _number_like(line["vietocr_text"])]
        grand_vector = _vector(
            numeric_lines[len(lane_types) :],
            lane_types,
            semantic_page["primary_numeric_authority"],
        )
        optional_margin = {
            "label_source_line_indices": [
                line["source_line_index"] for line in after[margin_offset:margin_label_end]
            ],
            "label_surface": " ".join(
                (
                    _semantic_match(line, _margin_text)
                    or ("VIETOCR_TRANSFORMER", line["vietocr_text"])
                )[1]
                for line in after[margin_offset:margin_label_end]
            ),
            "report_norm_id_candidate": 5747,
            "values": margin_vector or [],
        }
        total_variant = (
            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
            if core_vector is not None
            else "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
        )

    arithmetic_status = "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    if semantic_page["primary_numeric_authority"] and all(row["values"] for row in rows):
        row_money = [_money_values(row["values"]) for row in rows]
        if all(values is not None for values in row_money):
            typed_row_money = [values for values in row_money if values is not None]
            sums = [sum(values[index] for values in typed_row_money) for index in range(2)]
            core_money = _money_values(core_vector or []) if core_vector is not None else None
            margin_money = (
                _money_values(optional_margin["values"]) if optional_margin is not None else None
            )
            grand_money = _money_values(grand_vector or []) if grand_vector is not None else None
            core_ok = core_money == sums if core_money is not None else optional_margin is not None
            grand_ok = (
                grand_money == [sums[index] + margin_money[index] for index in range(2)]
                if grand_money is not None and margin_money is not None
                else optional_margin is None
            )
            percent_ok = True
            if "PERCENT" in lane_types:
                row_percent = [_percentage_values(row["values"]) for row in rows]
                total_percent = _percentage_values(core_vector or [])
                percent_ok = (
                    all(values is not None for values in row_percent)
                    and total_percent is not None
                    and [
                        sum(values[index] for values in row_percent if values is not None)
                        for index in range(2)
                    ]
                    == total_percent
                    == [Decimal("100.00"), Decimal("100.00")]
                )
            arithmetic_status = (
                "CORROBORATED_TYPED_POPULATIONS"
                if core_ok and grand_ok and percent_ok
                else "VETOED_POPULATION_MISMATCH"
            )
            if arithmetic_status.startswith("VETOED"):
                reasons.append("ARITHMETIC_POPULATION_VETO")

    schema_candidate_frontier_ready = (
        not reasons and arithmetic_status == "CORROBORATED_TYPED_POPULATIONS"
    )
    status = (
        "ACCEPTED_VARIANT_GRAPH"
        if schema_candidate_frontier_ready
        else (
            "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            if not reasons and arithmetic_status == "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            else "UNRESOLVED"
        )
    )
    graph = {
        "arithmetic_status": arithmetic_status,
        "axes": periods,
        "branch": {
            "match_kind": candidate["branch_match"]["match_kind"],
            "qwen35_challenger_text": lines[branch_index]["qwen35_challenger_text"],
            "semantic_source": candidate["branch_match"]["semantic_source"],
            "source_line_index": branch_index,
            "surface": candidate["branch_match"]["surface"],
            "variant": candidate["branch_match"]["variant"],
            "vietocr_text": lines[branch_index]["vietocr_text"],
        },
        "intermediate_header": next(
            (
                {
                    "semantic_source": match[0],
                    "source_line_index": line["source_line_index"],
                    "surface": match[1],
                }
                for line in header
                if (match := _semantic_match(line, _intermediate_header)) is not None
            ),
            None,
        ),
        "schema_candidate_frontier_ready": schema_candidate_frontier_ready,
        "optional_margin": optional_margin,
        "owner": owner,
        "parent_context_report_norm_id_candidate": 752,
        "period_mode": period_mode,
        "rows": rows,
        "schema_owner_report_norm_id_candidate": 716,
        "total": {
            "core_values": core_vector or [],
            "grand_values": grand_vector or [],
            "report_norm_id": None,
            "variant": total_variant,
        },
        "unit_scope": unit_scope,
    }
    return {
        "candidate_count": 1,
        "graph": graph,
        "status": status,
        "unresolved_reasons": sorted(set(reasons)),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-maturity variant graph result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["status"]
        not in {"ACCEPTED_VARIANT_GRAPH", "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED", "UNRESOLVED"}
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["document_candidate_count"]) is not int
        or value["document_candidate_count"] < 0
        or type(value["unresolved_reasons"]) is not list
        or value["unresolved_reasons"] != sorted(set(value["unresolved_reasons"]))
    ):
        raise _error("loan-maturity variant graph identity/safety drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("graph_id")
    if identity != "lmvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("loan-maturity variant graph identity drifted")
    metrics = value["metrics"]
    if type(metrics) is not dict or set(metrics) != {
        "document_candidate_count",
        "mapped_role_candidate_count",
        "optional_margin_count",
        "qwen_challenger_line_count",
        "qwen_semantic_match_use_count",
        "resolved_role_count",
    }:
        raise _error("loan-maturity variant graph metrics drifted")
    if any(type(item) is not int or item < 0 for item in metrics.values()):
        raise _error("loan-maturity variant graph metric types drifted")
    result = value["result"]
    if type(result) is not dict or set(result) != {
        "candidate_count",
        "graph",
        "status",
        "unresolved_reasons",
    }:
        raise _error("loan-maturity inner result fields drifted")
    if result["candidate_count"] != value["document_candidate_count"]:
        raise _error("loan-maturity candidate denominator drifted")
    return canonical_clone_v1(value)


def build_loan_maturity_variant_graph_v1(
    document_pages: Sequence[Mapping[str, Any]],
    fresh_semantic_page: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one deterministic variant graph without bank-specific routing."""

    if isinstance(document_pages, (str, bytes, bytearray)) or not document_pages:
        raise _error("document pages must be one non-empty sequence")
    pages = [
        _exact_page(page, f"document page {index}") for index, page in enumerate(document_pages)
    ]
    sequences = [page["page_sequence"] for page in pages]
    if sequences != sorted(sequences) or len(set(sequences)) != len(sequences):
        raise _error("document pages must be unique and ordered")
    semantic_page = _semantic_page(fresh_semantic_page)
    if semantic_page["page_sequence"] not in sequences:
        raise _error("fresh semantic page is not in the document denominator")
    inner = _build_result(pages, semantic_page)
    graph = inner["graph"]
    metrics = {
        "document_candidate_count": inner["candidate_count"],
        "mapped_role_candidate_count": (
            len(graph["rows"]) + (1 if graph["optional_margin"] is not None else 0)
            if graph is not None
            else 0
        ),
        "optional_margin_count": (
            1 if graph is not None and graph["optional_margin"] is not None else 0
        ),
        "qwen_challenger_line_count": sum(
            line["qwen35_challenger_text"] is not None for page in pages for line in page["lines"]
        ),
        "qwen_semantic_match_use_count": _qwen_source_count(graph),
        "resolved_role_count": len(graph["rows"]) if graph is not None else 0,
    }
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "document_candidate_count": inner["candidate_count"],
        "format_version": FORMAT_VERSION,
        "metrics": metrics,
        "result": inner,
        "safety": canonical_clone_v1(_SAFETY),
        "status": inner["status"],
        "unresolved_reasons": canonical_clone_v1(inner["unresolved_reasons"]),
    }
    return _validate_result(
        {**material, "graph_id": "lmvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def scan_loan_maturity_variant_graph_document_v1(
    document_pages: Sequence[Mapping[str, Any]],
    semantic_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Scan one complete PDF once and build only its unique candidate page.

    ``document_pages`` is the reference-blind Transformer text axis used for
    whole-document uniqueness.  ``semantic_pages`` adds the bound pixel boxes
    and optional source numeric text for those exact same Transformer lines.
    The function deliberately refuses a partial/misaligned page set instead of
    repeatedly searching the PDF once per page.
    """

    if (
        isinstance(document_pages, (str, bytes, bytearray))
        or isinstance(semantic_pages, (str, bytes, bytearray))
        or not document_pages
        or not semantic_pages
        or len(document_pages) != len(semantic_pages)
    ):
        raise _error("document scan requires two non-empty coextensive page sequences")
    pages = [
        _exact_page(page, f"document scan page {index}")
        for index, page in enumerate(document_pages)
    ]
    semantics = [_semantic_page(page, allow_empty=True) for page in semantic_pages]
    sequences = [page["page_sequence"] for page in pages]
    semantic_sequences = [page["page_sequence"] for page in semantics]
    if (
        sequences != sorted(sequences)
        or len(set(sequences)) != len(sequences)
        or semantic_sequences != sequences
    ):
        raise _error("document scan page sequences are not exact, unique, and ordered")
    for page, semantic in zip(pages, semantics, strict=True):
        if len(page["lines"]) != len(semantic["lines"]):
            raise _error("document scan semantic line denominator drifted")
        for document_line, semantic_line in zip(page["lines"], semantic["lines"], strict=True):
            if (
                document_line["source_line_index"] != semantic_line["source_line_index"]
                or document_line["vietocr_text"] != semantic_line["vietocr_text"]
                or document_line["qwen35_challenger_text"]
                != semantic_line["qwen35_challenger_text"]
            ):
                raise _error("document scan semantic text/order axis drifted")

    candidates = _document_candidates(pages)
    target_sequence = (
        candidates[0]["page_sequence"]
        if candidates
        else next(
            (page["page_sequence"] for page in semantics if page["lines"]),
            None,
        )
    )
    if target_sequence is None:
        raise _error("document scan contains no semantic lines")
    target = next(page for page in semantics if page["page_sequence"] == target_sequence)
    return build_loan_maturity_variant_graph_v1(pages, target)


def validate_loan_maturity_variant_graph_replay_v1(
    value: Any,
    document_pages: Sequence[Mapping[str, Any]],
    fresh_semantic_page: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild and exact-compare one persisted/projection value."""

    persisted = _validate_result(value)
    rebuilt = build_loan_maturity_variant_graph_v1(document_pages, fresh_semantic_page)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-maturity variant graph does not replay exactly")
    return canonical_clone_v1(rebuilt)
