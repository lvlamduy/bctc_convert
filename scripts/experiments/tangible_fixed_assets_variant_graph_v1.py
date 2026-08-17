"""Bank-blind full-PDF graph for tangible fixed-asset movements.

The common accounting core is an owner (tangible fixed assets), followed by
the cost, accumulated-depreciation and carrying-value branches.  Movement
rows, asset-class columns, comparison-page continuations and page rotation are
layout variants.  Text is an anchor only; numeric, period, unit, hierarchy and
accounting authority belong to the independent review layer.

No bank, filename, note number or physical page participates in matching.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.core.text import parse_vietnamese_dates
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
    "INTANGIBLE_FORMAT_VERSION",
    "INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE",
    "INVESTMENT_PROPERTY_FORMAT_VERSION",
    "INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE",
    "LEASED_FORMAT_VERSION",
    "LEASED_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE",
    "REPORTING_PERIOD_GENERAL_VARIANT_PROFILE",
    "TangibleFixedAssetsVariantGraphV1Error",
    "build_intangible_fixed_assets_variant_graph_document_v1",
    "build_investment_property_variant_graph_document_v1",
    "build_leased_fixed_assets_variant_graph_document_v1",
    "build_tangible_fixed_assets_variant_graph_document_v1",
    "validate_intangible_fixed_assets_variant_graph_replay_v1",
    "validate_investment_property_variant_graph_replay_v1",
    "validate_leased_fixed_assets_variant_graph_replay_v1",
    "validate_tangible_fixed_assets_variant_graph_replay_v1",
]

FORMAT_VERSION = "TANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "TANGIBLE_FIXED_ASSET_MOVEMENT"
REPORTING_PERIOD_GENERAL_FORMAT_VERSION = "TANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V2"
CURRENT_VARIANT_PROFILE = "CURRENT_V1"
REPORTING_PERIOD_GENERAL_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
LEASED_FORMAT_VERSION = "LEASED_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
LEASED_REPORTING_PERIOD_GENERAL_FORMAT_VERSION = "LEASED_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V2"
LEASED_FAMILY_ID = "LEASED_FIXED_ASSET_MOVEMENT"
LEASED_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
INTANGIBLE_FORMAT_VERSION = "INTANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V1"
INTANGIBLE_REPORTING_PERIOD_GENERAL_FORMAT_VERSION = (
    "INTANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V2"
)
INTANGIBLE_FAMILY_ID = "INTANGIBLE_FIXED_ASSET_MOVEMENT"
INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
INVESTMENT_PROPERTY_FORMAT_VERSION = "INVESTMENT_PROPERTY_VARIANT_GRAPH_DOCUMENT_V1"
INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_FORMAT_VERSION = (
    "INVESTMENT_PROPERTY_VARIANT_GRAPH_DOCUMENT_V2"
)
INVESTMENT_PROPERTY_FAMILY_ID = "INVESTMENT_PROPERTY_MOVEMENT"
INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE = "REPORTING_PERIOD_GENERAL_V2"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_TANGIBLE_FIXED_ASSET_OWNER_COST_"
    "ACCUMULATED_DEPRECIATION_CARRYING_VALUE_OPTIONAL_MOVEMENTS_ASSET_CLASS_"
    "COLUMNS_COMPARATIVE_CONTINUATION_AND_ROTATED_SOURCE_AXIS_STRUCTURE_ONLY_"
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
    "optional_movements_and_asset_class_columns_may_vary": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "rotated_same_transformer_rescue_may_supply_semantic_text": True,
    "text_similarity_alone_can_accept": False,
}
_REPORTING_PERIOD_GENERAL_SAFETY = {
    **canonical_clone_v1(_SAFETY),
    "dated_balance_roles_derived_from_chronology_not_fixed_calendar_dates": True,
    "latest_explicit_local_period_selects_current_table": True,
    "relative_beginning_and_ending_year_labels_supported": True,
}
_LEASED_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_LEASED_FIXED_ASSET_OWNER_COST_"
    "ACCUMULATED_DEPRECIATION_OPTIONAL_MOVEMENTS_ASSET_CLASS_COLUMNS_"
    "COMPARATIVE_CONTINUATION_AND_ROTATED_SOURCE_AXIS_STRUCTURE_ONLY_NO_"
    "NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_LEASED_SAFETY = canonical_clone_v1(_SAFETY)
_LEASED_REPORTING_PERIOD_GENERAL_SAFETY = {
    **canonical_clone_v1(_LEASED_SAFETY),
    "dated_balance_roles_derived_from_chronology_not_fixed_calendar_dates": True,
    "latest_explicit_local_period_selects_current_table": True,
    "relative_beginning_and_ending_year_labels_supported": True,
}
_INTANGIBLE_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_INTANGIBLE_FIXED_ASSET_OWNER_COST_"
    "ACCUMULATED_AMORTIZATION_CARRYING_VALUE_OPTIONAL_MOVEMENTS_ASSET_CLASS_"
    "COLUMNS_CURRENT_COMPARATIVE_PERIOD_VARIANTS_AND_SOURCE_AXIS_STRUCTURE_"
    "ONLY_NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_INTANGIBLE_SAFETY = canonical_clone_v1(_SAFETY)
_INTANGIBLE_REPORTING_PERIOD_GENERAL_SAFETY = {
    **canonical_clone_v1(_INTANGIBLE_SAFETY),
    "dated_balance_roles_derived_from_chronology_not_fixed_calendar_dates": True,
    "latest_explicit_local_period_selects_current_table": True,
    "first_complete_ordered_core_cycle_selected_before_later_detail_rows": True,
    "relative_beginning_and_ending_year_labels_supported": True,
}
_INVESTMENT_PROPERTY_CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_INVESTMENT_PROPERTY_OWNER_COST_"
    "ACCUMULATED_DEPRECIATION_CARRYING_VALUE_OPTIONAL_MOVEMENTS_ASSET_CLASS_"
    "COLUMNS_SAME_PAGE_CURRENT_COMPARATIVE_PERIOD_PARTITION_STRUCTURE_ONLY_"
    "NO_NUMERIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_INVESTMENT_PROPERTY_SAFETY = {
    **canonical_clone_v1(_SAFETY),
    "latest_explicit_period_selects_current_region": True,
    "same_page_comparative_region_retained": True,
}
_INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_SAFETY = {
    **canonical_clone_v1(_INVESTMENT_PROPERTY_SAFETY),
    "dated_balance_roles_derived_from_chronology_not_fixed_calendar_dates": True,
    "relative_beginning_and_ending_year_labels_supported": True,
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
_SEMANTIC_SOURCES = {
    "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
    "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE",
}
_NUMBER = re.compile(r"^\(?[+-]?[0-9]+(?:[., ][0-9]+)*%?\)?$")
_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|"
    r"(?:so\s+du\s+(?:dau|cuoi)\s+ky)|(?:tai\s+ngay\s+(?:dau|cuoi)\s+ky)"
)
_REPORTING_PERIOD_GENERAL_DATE = re.compile(
    r"(?:[0-3]?[0-9](?:[./-]|\s+)[01]?[0-9](?:[./-]|\s+)(?:20)?[0-9]{2})|"
    r"(?:ngay\s+[0-3]?[0-9]\s+thang\s+[01]?[0-9])|"
    r"(?:so\s+(?:du\s+)?(?:dau|cuoi)\s+(?:ky|nam))|"
    r"(?:tai\s+ngay\s+(?:dau|cuoi)\s+(?:ky|nam))"
)
_MAX_REGION_PAGES = 2

_TANGIBLE_SPEC = {
    "claim_boundary": CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION", "CARRYING_VALUE"),
    "family_id": FAMILY_ID,
    "format_version": FORMAT_VERSION,
    "id_prefix": "tfavgv1:result:",
    "minimum_numeric_lines": 6,
    "owner_left_region_only": False,
    "owner_phrases": ("tai san co dinh huu hinh",),
    "owner_reject_phrases": ("thong tin khac", "nguyen gia", "bien dong"),
    "safety": _SAFETY,
    "trailing_family_phrases": (
        "tai san co dinh thue tai chinh",
        "tai san co dinh vo hinh",
        "bat dong san dau tu",
    ),
}
_TANGIBLE_REPORTING_PERIOD_GENERAL_SPEC = {
    **_TANGIBLE_SPEC,
    "branch_reject_phrases": ("da khau hao het",),
    "dynamic_dated_balance_roles": True,
    "format_version": REPORTING_PERIOD_GENERAL_FORMAT_VERSION,
    "id_prefix": "tfavgv2:result:",
    "latest_explicit_period_selects_current_region": True,
    "owner_phrases": (
        "tai san co dinh huu hinh",
        "tai san co dinh tscd huu hinh",
    ),
    "period_pattern": _REPORTING_PERIOD_GENERAL_DATE,
    "relative_year_balance_roles": True,
    "rotated_coordinate_window": True,
    "safety": _REPORTING_PERIOD_GENERAL_SAFETY,
}
_LEASED_SPEC = {
    "claim_boundary": _LEASED_CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION"),
    "family_id": LEASED_FAMILY_ID,
    "format_version": LEASED_FORMAT_VERSION,
    "id_prefix": "lfavgv1:result:",
    "minimum_numeric_lines": 4,
    "owner_left_region_only": False,
    "owner_phrases": ("tai san co dinh thue tai chinh", "tscd thue tai chinh"),
    "owner_reject_phrases": ("thong tin khac", "nguyen tac", "chinh sach"),
    "safety": _LEASED_SAFETY,
    "trailing_family_phrases": ("tai san co dinh vo hinh", "bat dong san dau tu"),
}
_LEASED_REPORTING_PERIOD_GENERAL_SPEC = {
    **_LEASED_SPEC,
    "adjacent_line_anchor_fusion": True,
    "dynamic_dated_balance_roles": True,
    "format_version": LEASED_REPORTING_PERIOD_GENERAL_FORMAT_VERSION,
    "id_prefix": "lfavgv2:result:",
    "latest_explicit_period_selects_current_region": True,
    "period_pattern": _REPORTING_PERIOD_GENERAL_DATE,
    "relative_year_balance_roles": True,
    "rotated_coordinate_window": True,
    "safety": _LEASED_REPORTING_PERIOD_GENERAL_SAFETY,
}
_INTANGIBLE_SPEC = {
    "claim_boundary": _INTANGIBLE_CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION", "CARRYING_VALUE"),
    "family_id": INTANGIBLE_FAMILY_ID,
    "format_version": INTANGIBLE_FORMAT_VERSION,
    "id_prefix": "ifavgv1:result:",
    "minimum_numeric_lines": 6,
    "owner_left_region_only": True,
    "owner_phrases": ("tai san co dinh vo hinh", "tscd vo hinh"),
    "owner_reject_phrases": (
        "thong tin khac",
        "nguyen gia",
        "bien dong",
        "chinh sach",
        "hao mon",
    ),
    "safety": _INTANGIBLE_SAFETY,
    "trailing_family_phrases": (
        "bat dong san dau tu",
        "xay dung co ban do dang",
        "tai san co khac",
        "cac khoan no chinh phu",
    ),
}
_INTANGIBLE_REPORTING_PERIOD_GENERAL_SPEC = {
    **_INTANGIBLE_SPEC,
    "adjacent_line_anchor_fusion": True,
    "branch_same_page_required": False,
    "branch_reject_phrases": ("da hao mon het", "da khau hao het"),
    "dynamic_dated_balance_roles": True,
    "format_version": INTANGIBLE_REPORTING_PERIOD_GENERAL_FORMAT_VERSION,
    "first_ordered_core_cycle": True,
    "id_prefix": "ifavgv2:result:",
    "latest_explicit_period_selects_current_region": True,
    "owner_left_region_only": False,
    "owner_reject_phrases": (
        *_INTANGIBLE_SPEC["owner_reject_phrases"],
        "co gia tri lon",
        "gia tri con lai",
        "phan mem",
        "quyen su dung dat",
        "vi tinh",
        "vo hinh khac",
    ),
    "period_pattern": _REPORTING_PERIOD_GENERAL_DATE,
    "relative_year_balance_roles": True,
    "rotated_coordinate_window": True,
    "safety": _INTANGIBLE_REPORTING_PERIOD_GENERAL_SAFETY,
    "split_repeated_branch_cycles": True,
}
_INVESTMENT_PROPERTY_SPEC = {
    "branch_same_page_required": False,
    "branch_phrases": {
        "ACCUMULATED_DEPRECIATION": (
            "gia tri hao mon",
            "gia tri hao mon luy ke",
            "hao mon luy ke",
            "khau hao luy ke",
        ),
        "CARRYING_VALUE": ("gia tri con lai",),
        "COST": ("nguyen gia",),
    },
    "claim_boundary": _INVESTMENT_PROPERTY_CLAIM_BOUNDARY,
    "core_roles": ("COST", "ACCUMULATED_DEPRECIATION", "CARRYING_VALUE"),
    "family_id": INVESTMENT_PROPERTY_FAMILY_ID,
    "format_version": INVESTMENT_PROPERTY_FORMAT_VERSION,
    "id_prefix": "ipavgv1:result:",
    "minimum_numeric_lines": 6,
    "minimum_period_lines": 1,
    "owner_left_region_only": True,
    "owner_phrases": ("bat dong san dau tu", "bds dau tu"),
    "owner_reject_phrases": (
        "chuyen sang",
        "chuyen tu",
        "gia tri hao mon",
        "hao mon",
        "khau hao tscd",
        "mua sam",
        "nguyen gia",
        "thanh ly",
        "thong tin khac",
        "tien thu",
    ),
    "safety": _INVESTMENT_PROPERTY_SAFETY,
    "trailing_family_phrases": (
        "tai san co khac",
        "cac khoan no chinh phu",
        "tien gui cua khach hang",
    ),
}
_INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_SPEC = {
    **_INVESTMENT_PROPERTY_SPEC,
    "adjacent_line_anchor_fusion": True,
    "dynamic_dated_balance_roles": True,
    "format_version": INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_FORMAT_VERSION,
    "id_prefix": "ipavgv2:result:",
    "period_pattern": _REPORTING_PERIOD_GENERAL_DATE,
    "relative_year_balance_roles": True,
    "rotated_coordinate_window": True,
    "safety": _INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_SAFETY,
}


class TangibleFixedAssetsVariantGraphV1Error(ValueError):
    """The complete-PDF input or replayed tangible-asset graph drifted."""


def _error(message: str) -> TangibleFixedAssetsVariantGraphV1Error:
    return TangibleFixedAssetsVariantGraphV1Error(message)


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
        raise _error("tangible-fixed-assets matcher requires one complete nonempty PDF")
    pages: list[dict[str, Any]] = []
    global_ordinal = 0
    previous_page = 0
    for raw_page in value:
        if type(raw_page) is not dict or set(raw_page) != {
            "lines",
            "page_sequence",
            "primary_numeric_authority",
        }:
            raise _error("tangible-fixed-assets matcher page fields drifted")
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
                raise _error("tangible-fixed-assets line fields drifted")
            if raw_line["source_line_index"] != line_index:
                raise _error("source line indices must be exact and gap-free")
            if raw_line["source_text"] is not None and type(raw_line["source_text"]) is not str:
                raise _error("source text must be null or one exact string")
            if (
                type(raw_line["vietocr_text"]) is not str
                or type(raw_line["semantic_text"]) is not str
            ):
                raise _error("VietOCR and semantic text must be exact strings")
            if raw_line["semantic_text_source"] not in _SEMANTIC_SOURCES:
                raise _error("semantic text source is unsupported")
            lines.append(
                {
                    "bbox": _bbox(raw_line["bbox"]),
                    "global_ordinal": global_ordinal,
                    "normalized_text": normalize_vietnamese_anchor_v1(raw_line["semantic_text"]),
                    "page_sequence": page_sequence,
                    "semantic_text": raw_line["semantic_text"],
                    "semantic_text_source": raw_line["semantic_text_source"],
                    "source_line_index": line_index,
                    "source_text": raw_line["source_text"],
                    "vietocr_text": raw_line["vietocr_text"],
                }
            )
            global_ordinal += 1
        for index, line in enumerate(lines[:-1]):
            following = lines[index + 1]
            height = max(line["bbox"][3] - line["bbox"][1], 1)
            following_height = max(following["bbox"][3] - following["bbox"][1], 1)
            vertical_gap = following["bbox"][1] - line["bbox"][3]
            left_edge_gap = abs(following["bbox"][0] - line["bbox"][0])
            horizontally_related = not (
                following["bbox"][0] > line["bbox"][2] + max(height, following_height) * 2
                or line["bbox"][0] > following["bbox"][2] + max(height, following_height) * 2
            )
            current_text = line["normalized_text"]
            following_text = following["normalized_text"]
            current_is_complete_axis_or_value = (
                not current_text
                or _NUMBER.fullmatch(current_text.replace(" ", "")) is not None
                or current_text.startswith(
                    (
                        "so du ",
                        "tai ngay ",
                        "mua ",
                        "tang ",
                        "giam ",
                        "thanh ly",
                        "nhuong ban",
                        "khau hao trong",
                        "phan loai ",
                        "chenh lech ",
                        "tong cong",
                        "trieu dong",
                        "trieu vnd",
                    )
                )
            )
            following_is_value = _NUMBER.fullmatch(following_text.replace(" ", "")) is not None
            if (
                -max(height, following_height) // 2
                <= vertical_gap
                <= max(height, following_height) * 2
                and horizontally_related
                and left_edge_gap <= max(height, following_height) * 4
                and not current_is_complete_axis_or_value
                and not following_is_value
            ):
                line["normalized_text_with_next"] = " ".join(
                    part for part in (line["normalized_text"], following["normalized_text"]) if part
                )
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


def _is_owner(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> bool:
    value = _strip_enumerator(text)
    if any(prefix in value for prefix in spec["owner_reject_phrases"]):
        return False
    return len(value.split()) <= 11 and any(
        _near_phrase(value, phrase, allowance=2) for phrase in spec["owner_phrases"]
    )


def _anchor_texts(line: Mapping[str, Any], spec: Mapping[str, Any]) -> tuple[str, ...]:
    texts = [line["normalized_text"]]
    fused = line.get("normalized_text_with_next")
    if spec.get("adjacent_line_anchor_fusion", False) and type(fused) is str and fused:
        texts.append(fused)
    return tuple(texts)


def _is_owner_line(line: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    return any(_is_owner(text, spec) for text in _anchor_texts(line, spec))


def _is_next_family_line(line: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    return any(_is_next_family(text, spec) for text in _anchor_texts(line, spec))


def _branch_role_line(line: Mapping[str, Any], spec: Mapping[str, Any]) -> str | None:
    for text in _anchor_texts(line, spec):
        role = _branch_role(text, spec)
        if role is not None:
            return role
    return None


def _owner_layout_eligible(
    line: Mapping[str, Any], page: Mapping[str, Any], spec: Mapping[str, Any]
) -> bool:
    if not spec["owner_left_region_only"]:
        return True
    page_right = max((item["bbox"][2] for item in page["lines"]), default=0)
    return page_right > 0 and line["bbox"][0] * 2 <= page_right


def _is_next_family(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> bool:
    value = _strip_enumerator(text)
    return len(value.split()) <= 12 and any(
        _near_phrase(value, phrase, allowance=2) for phrase in spec["trailing_family_phrases"]
    )


def _branch_role(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 10 or any(
        phrase in value for phrase in spec.get("branch_reject_phrases", ())
    ):
        return None
    phrases = spec.get(
        "branch_phrases",
        {
            "ACCUMULATED_DEPRECIATION": (
                "hao mon luy ke",
                "khau hao luy ke",
                "gia tri hao mon luy ke",
            ),
            "CARRYING_VALUE": ("gia tri con lai",),
            "COST": ("nguyen gia",),
        },
    )
    for role in ("COST", "ACCUMULATED_DEPRECIATION", "CARRYING_VALUE"):
        if any(_near_phrase(value, phrase, allowance=2) for phrase in phrases[role]):
            return role
    return None


def _movement_role(text: str, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> str | None:
    value = _strip_enumerator(text)
    if len(value.split()) > 14:
        return None
    annual = spec.get("relative_year_balance_roles", False)
    rules = (
        (
            "OPENING",
            (
                "so du dau ky",
                "tai ngay dau ky",
                *(("so du dau nam", "so dau nam", "tai ngay dau nam") if annual else ()),
                *(("tai ngay 1 1",) if not annual else ()),
            ),
        ),
        (
            "ENDING",
            (
                "so du cuoi ky",
                "tai ngay cuoi ky",
                *(("so du cuoi nam", "so cuoi nam", "tai ngay cuoi nam") if annual else ()),
                *(("tai ngay 30 06",) if not annual else ()),
            ),
        ),
        ("PURCHASE", ("mua trong ky", *(("mua trong nam",) if annual else ()))),
        (
            "DEPRECIATION",
            ("khau hao trong ky", *(("khau hao trong nam",) if annual else ())),
        ),
        ("INCREASE", ("tang trong ky", *(("tang trong nam",) if annual else ()))),
        ("DECREASE", ("giam trong ky", *(("giam trong nam",) if annual else ()))),
        (
            "OTHER_NET",
            ("tang giam khac", *(("tang khac", "giam khac") if annual else ())),
        ),
        ("FOREIGN_EXCHANGE", ("chenh lech ty gia",)),
        ("DISPOSAL", ("thanh ly", "nhuong ban")),
        (
            "RECLASSIFICATION",
            ("phan loai lai", *(("phan loai lai trong nam",) if annual else ())),
        ),
    )
    for role, phrases in rules:
        if any(_near_phrase(value, phrase, allowance=2) for phrase in phrases):
            return role
    return None


def _dated_balance_roles(
    window: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> dict[int, str]:
    """Infer dated balance-row roles from chronology, never calendar constants."""

    if not spec.get("dynamic_dated_balance_roles", False):
        return {}
    candidates: list[tuple[Mapping[str, Any], Any]] = []
    for line in window:
        value = _strip_enumerator(line["normalized_text"])
        if not value.startswith(("tai ngay ", "so du tai ngay ")):
            continue
        parsed = parse_vietnamese_dates(line["semantic_text"])
        if len(parsed) == 1:
            candidates.append((line, parsed[0]))
    dates = {parsed for _line, parsed in candidates}
    if len(dates) < 2:
        return {}
    opening = min(dates)
    ending = max(dates)
    return {
        line["global_ordinal"]: "OPENING" if parsed == opening else "ENDING"
        for line, parsed in candidates
        if parsed in {opening, ending}
    }


def _line_ref(line: Mapping[str, Any], role: str) -> dict[str, Any]:
    return {
        "bbox": list(line["bbox"]),
        "global_ordinal": line["global_ordinal"],
        "page_sequence": line["page_sequence"],
        "role": role,
        "semantic_text": line["semantic_text"],
        "semantic_text_source": line["semantic_text_source"],
        "source_line_index": line["source_line_index"],
        "vietocr_text": line["vietocr_text"],
    }


def _is_rotated(lines: Sequence[Mapping[str, Any]]) -> bool:
    if not lines:
        return False
    tall = sum(
        line["bbox"][3] - line["bbox"][1] > line["bbox"][2] - line["bbox"][0] for line in lines
    )
    rescued = sum(
        line["semantic_text_source"] == "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE" for line in lines
    )
    return tall * 2 > len(lines) and rescued > 0


def _logical_position(line: Mapping[str, Any], *, rotated: bool) -> tuple[int, int]:
    if rotated:
        return line["bbox"][0], line["bbox"][1]
    return line["global_ordinal"], 0


def _candidate_window(
    owner: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] = _TANGIBLE_SPEC,
) -> tuple[list[Mapping[str, Any]], bool]:
    owner_page = pages[owner["page_sequence"] - 1]
    rotated = _is_rotated(owner_page["lines"])
    if rotated and spec.get("rotated_coordinate_window", False):
        # Provider order on a landscape table follows extraction columns and can
        # put numeric cells before the section/branch labels.  Reconstruct the
        # table's vertical reading axis from geometry, while retaining the
        # provider line identities and semantic evidence unchanged.
        owner_position = _logical_position(owner, rotated=True)
        selected = []
        for line in sorted(
            owner_page["lines"], key=lambda item: _logical_position(item, rotated=True)
        ):
            if _logical_position(line, rotated=True) < owner_position:
                continue
            if line is not owner and (
                (_is_owner_line(line, spec) and _owner_layout_eligible(line, owner_page, spec))
                or _is_next_family_line(line, spec)
            ):
                break
            selected.append(line)
        return selected, True
    selected: list[Mapping[str, Any]] = []
    for page in pages[owner["page_sequence"] - 1 : owner["page_sequence"] - 1 + _MAX_REGION_PAGES]:
        if page["page_sequence"] != owner["page_sequence"] and any(
            _is_next_family_line(line, spec) for line in page["lines"]
        ):
            break
        for line in page["lines"]:
            if page["page_sequence"] == owner["page_sequence"] and not rotated:
                if line["global_ordinal"] < owner["global_ordinal"]:
                    continue
            if (
                line is not owner
                and _is_owner_line(line, spec)
                and _owner_layout_eligible(line, page, spec)
            ):
                break
            if _is_next_family_line(line, spec):
                break
            selected.append(line)
    return selected, rotated


def _region(
    owner: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] = _TANGIBLE_SPEC,
) -> dict[str, Any]:
    window, rotated = _candidate_window(owner, pages, spec)
    return _region_from_window(owner, window, rotated=rotated, spec=spec)


def _region_from_window(
    owner: Mapping[str, Any],
    window: Sequence[Mapping[str, Any]],
    *,
    rotated: bool,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    branches: dict[str, list[Mapping[str, Any]]] = {}
    movements: dict[str, list[Mapping[str, Any]]] = {}
    periods: list[Mapping[str, Any]] = []
    units: list[Mapping[str, Any]] = []
    numeric_lines: list[Mapping[str, Any]] = []
    dated_balance_roles = _dated_balance_roles(window, spec)
    period_pattern = spec.get("period_pattern", _DATE)
    for line in window:
        text = line["normalized_text"]
        branch = _branch_role_line(line, spec)
        movement = _movement_role(text, spec)
        if movement is None:
            movement = dated_balance_roles.get(line["global_ordinal"])
        if branch is not None:
            branches.setdefault(branch, []).append(line)
        if movement is not None:
            movements.setdefault(movement, []).append(line)
        if period_pattern.search(text) or (
            spec.get("dynamic_dated_balance_roles", False)
            and parse_vietnamese_dates(line["semantic_text"])
        ):
            periods.append(line)
        if "trieu dong" in text or "trieu vnd" in text:
            units.append(line)
        if _NUMBER.fullmatch(text.replace(" ", "")):
            numeric_lines.append(line)
    core_roles = spec["core_roles"]
    branch_candidates = {
        role: (
            [
                line
                for line in branches.get(role, [])
                if line["page_sequence"] == owner["page_sequence"]
            ]
            if spec.get("branch_same_page_required", True)
            else list(branches.get(role, []))
        )
        for role in core_roles
    }
    if spec.get("first_ordered_core_cycle", False):
        current_branches: dict[str, list[Mapping[str, Any]]] = {}
        cursor = _logical_position(owner, rotated=rotated)
        for role in core_roles:
            eligible = sorted(
                (
                    line
                    for line in branch_candidates[role]
                    if _logical_position(line, rotated=rotated) > cursor
                ),
                key=lambda line: _logical_position(line, rotated=rotated),
            )
            current_branches[role] = eligible[:1]
            if eligible:
                cursor = _logical_position(eligible[0], rotated=rotated)
    else:
        current_branches = branch_candidates
    unique_branches = all(len(current_branches[role]) == 1 for role in core_roles)
    ordered = False
    if unique_branches:
        positions = [
            _logical_position(current_branches[role][0], rotated=rotated) for role in core_roles
        ]
        owner_position = _logical_position(owner, rotated=rotated)
        ordered = owner_position < positions[0] and all(
            left < right for left, right in itertools.pairwise(positions)
        )
    complete = (
        unique_branches
        and ordered
        and len(periods) >= spec.get("minimum_period_lines", 2)
        and len(units) >= 1
        and len(numeric_lines) >= spec["minimum_numeric_lines"]
        and "OPENING" in movements
        and "ENDING" in movements
    )
    anchor_roles = ["OWNER", *[role for role in core_roles if role in branches]]
    events = [_line_ref(owner, "OWNER")]
    for role in core_roles:
        events.extend(_line_ref(line, role) for line in branches.get(role, []))
    for role in sorted(movements):
        events.extend(_line_ref(line, role) for line in movements[role])
    events.extend(_line_ref(line, "PERIOD_AXIS") for line in periods[:8])
    events.extend(_line_ref(line, "UNIT_AXIS") for line in units[:6])
    page_span = sorted({line["page_sequence"] for line in window}) or [owner["page_sequence"]]
    return {
        "anchor_roles": anchor_roles,
        "complete": complete,
        "end_global_ordinal": max(
            (line["global_ordinal"] for line in window), default=owner["global_ordinal"]
        ),
        "events": events,
        "layout": {
            "branch_order_verified": ordered,
            "branch_roles": sorted(branches),
            "explicit_unit_line_count": len(units),
            "movement_roles": sorted(movements),
            "period_axis_line_count": len(periods),
            "presentation": (
                "ROTATED_VERTICAL_SOURCE_AXIS_MOVEMENT_GRID"
                if rotated
                else (
                    "CURRENT_TABLE_WITH_COMPARATIVE_CONTINUATION"
                    if len(page_span) == 2
                    else "CURRENT_PERIOD_MOVEMENT_GRID"
                )
            ),
            "rotated_source_axis": rotated,
        },
        "numeric_line_count": len(numeric_lines),
        "owner": _line_ref(owner, "OWNER"),
        "pair_anchor_combinations": [
            list(pair) for pair in itertools.combinations(anchor_roles, 2)
        ],
        "page_span": [page_span[0], page_span[-1]],
        "start_global_ordinal": min(
            (line["global_ordinal"] for line in window), default=owner["global_ordinal"]
        ),
    }


def _local_period_end_rank(
    owner: Mapping[str, Any],
    window: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> tuple[int, int, int] | None:
    """Read the local table heading after its owner and before its first branch."""

    if not spec.get("latest_explicit_period_selects_current_region", False):
        return None
    dates = []
    for line in window:
        if line["global_ordinal"] == owner["global_ordinal"]:
            continue
        if _branch_role_line(line, spec) is not None:
            break
        dates.extend(parse_vietnamese_dates(line["semantic_text"]))
    if not dates:
        return None
    latest = max(dates)
    return latest.year, latest.month, latest.day


def _select_latest_explicit_period_region(
    records: Sequence[tuple[dict[str, Any], tuple[int, int, int] | None]],
    spec: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Retain one newest complete table and quarantine older comparison tables."""

    candidates = [canonical_clone_v1(candidate) for candidate, _rank in records]
    if not spec.get("latest_explicit_period_selects_current_region", False):
        return candidates
    complete_records = [
        (index, rank) for index, (candidate, rank) in enumerate(records) if candidate["complete"]
    ]
    if len(complete_records) < 2 or any(rank is None for _index, rank in complete_records):
        return candidates
    newest = max(rank for _index, rank in complete_records if rank is not None)
    selected = [index for index, rank in complete_records if rank == newest]
    if len(selected) != 1:
        return candidates
    selected_index = selected[0]
    candidates[selected_index]["layout"]["selected_as_latest_explicit_period"] = True
    for index, _rank in complete_records:
        if index == selected_index:
            continue
        candidates[index]["complete"] = False
        candidates[index]["layout"]["comparison_period_control"] = True
        candidates[index]["layout"]["selected_as_latest_explicit_period"] = False
    return candidates


def _candidate_cycle_windows(
    window: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> list[list[Mapping[str, Any]]]:
    """Split repeated annual branch cycles under one shared owner."""

    material = list(window)
    if not spec.get("split_repeated_branch_cycles", False):
        return [material]
    cost_indices = [
        index for index, line in enumerate(material) if _branch_role_line(line, spec) == "COST"
    ]
    if len(cost_indices) <= 1:
        return [material]
    starts = [0]
    for previous_cost, cost_index in itertools.pairwise(cost_indices):
        dated = [
            index
            for index in range(previous_cost + 1, cost_index)
            if parse_vietnamese_dates(material[index]["semantic_text"])
        ]
        if not dated:
            return [material]
        starts.append(dated[-1])
    if len(set(starts)) != len(cost_indices):
        return [material]
    return [
        material[start:end] for start, end in zip(starts, [*starts[1:], len(material)], strict=True)
    ]


def _validate_result(value: Any, spec: Mapping[str, Any] = _TANGIBLE_SPEC) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("tangible-fixed-assets graph result fields drifted")
    if (
        value["format_version"] != spec["format_version"]
        or value["family_id"] != spec["family_id"]
        or value["claim_boundary"] != spec["claim_boundary"]
        or not same_typed_json_v1(value["safety"], spec["safety"])
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or type(value["metrics"]) is not dict
        or type(value["uniqueness"]) is not dict
    ):
        raise _error("tangible-fixed-assets graph identity or authority drifted")
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
        raise _error("tangible-fixed-assets graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != spec["id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("tangible-fixed-assets graph identity drifted")
    return canonical_clone_v1(value)


def _build_variant_graph_document_v1(pages: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    normalized_pages = _pages(pages)
    owners = [
        line
        for page in normalized_pages
        for line in page["lines"]
        if _is_owner_line(line, spec) and _owner_layout_eligible(line, page, spec)
    ]
    records = []
    for owner in owners:
        window, rotated = _candidate_window(owner, normalized_pages, spec)
        for cycle_window in _candidate_cycle_windows(window, spec):
            candidate = _region_from_window(owner, cycle_window, rotated=rotated, spec=spec)
            records.append((candidate, _local_period_end_rank(owner, cycle_window, spec)))
    candidates = _select_latest_explicit_period_region(records, spec)
    regions = [candidate for candidate in candidates if candidate["complete"]]
    near_regions = [candidate for candidate in candidates if not candidate["complete"]]
    material = {
        "claim_boundary": spec["claim_boundary"],
        "family_id": spec["family_id"],
        "format_version": spec["format_version"],
        "metrics": {
            "complete_region_count": len(regions),
            "near_region_count": len(near_regions),
            "owner_candidate_count": len(candidates),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(spec["safety"]),
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
        {**material, "result_id": spec["id_prefix"] + canonical_json_sha256_v1(material)},
        spec,
    )


def _tangible_spec(variant_profile: str) -> Mapping[str, Any]:
    if variant_profile == CURRENT_VARIANT_PROFILE:
        return _TANGIBLE_SPEC
    if variant_profile == REPORTING_PERIOD_GENERAL_VARIANT_PROFILE:
        return _TANGIBLE_REPORTING_PERIOD_GENERAL_SPEC
    raise _error("tangible-fixed-assets variant profile drifted")


def build_tangible_fixed_assets_variant_graph_document_v1(
    pages: Any, *, variant_profile: str = CURRENT_VARIANT_PROFILE
) -> dict[str, Any]:
    """Enumerate every complete and near-complete tangible-asset region."""

    return _build_variant_graph_document_v1(pages, _tangible_spec(variant_profile))


def _leased_spec(variant_profile: str) -> Mapping[str, Any]:
    if variant_profile == CURRENT_VARIANT_PROFILE:
        return _LEASED_SPEC
    if variant_profile == LEASED_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE:
        return _LEASED_REPORTING_PERIOD_GENERAL_SPEC
    raise _error("leased-fixed-assets variant profile drifted")


def build_leased_fixed_assets_variant_graph_document_v1(
    pages: Any, *, variant_profile: str = CURRENT_VARIANT_PROFILE
) -> dict[str, Any]:
    """Enumerate every complete and near-complete leased-asset region."""

    return _build_variant_graph_document_v1(pages, _leased_spec(variant_profile))


def _intangible_spec(variant_profile: str) -> Mapping[str, Any]:
    if variant_profile == CURRENT_VARIANT_PROFILE:
        return _INTANGIBLE_SPEC
    if variant_profile == INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE:
        return _INTANGIBLE_REPORTING_PERIOD_GENERAL_SPEC
    raise _error("intangible-fixed-assets variant profile drifted")


def build_intangible_fixed_assets_variant_graph_document_v1(
    pages: Any, *, variant_profile: str = CURRENT_VARIANT_PROFILE
) -> dict[str, Any]:
    """Enumerate every complete and near-complete intangible-asset region."""

    return _build_variant_graph_document_v1(pages, _intangible_spec(variant_profile))


_EXPLICIT_PERIOD_END = re.compile(
    r"(?:ngay\s+)?([0-3]?[0-9])\s+thang\s+([01]?[0-9])\s+nam\s+((?:20)?[0-9]{2})"
)


def _period_end_rank(lines: Sequence[Mapping[str, Any]]) -> tuple[int, int, int] | None:
    ranks: list[tuple[int, int, int]] = []
    for line in lines:
        for day, month, year in _EXPLICIT_PERIOD_END.findall(line["normalized_text"]):
            normalized_year = int(year)
            if normalized_year < 100:
                normalized_year += 2000
            ranks.append((normalized_year, int(month), int(day)))
    return max(ranks, default=None)


def _investment_property_owner_candidates(
    owner: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> list[dict[str, Any]]:
    window, rotated = _candidate_window(owner, pages, spec)
    period_pattern = spec.get("period_pattern", _DATE)
    section_starts = [
        index
        for index, line in enumerate(window)
        if "bat dong san dau tu" in line["normalized_text"]
        and period_pattern.search(line["normalized_text"])
    ]
    sections: list[Sequence[Mapping[str, Any]]]
    if section_starts:
        sections = [
            window[start : section_starts[index + 1]]
            if index + 1 < len(section_starts)
            else window[start:]
            for index, start in enumerate(section_starts)
        ]
    else:
        sections = [window]
    result = []
    for section in sections:
        candidate = _region_from_window(owner, section, rotated=rotated, spec=spec)
        rank = _period_end_rank(section)
        candidate["period_end"] = None if rank is None else list(rank)
        result.append(candidate)
    return result


def _investment_property_spec(variant_profile: str) -> Mapping[str, Any]:
    if variant_profile == CURRENT_VARIANT_PROFILE:
        return _INVESTMENT_PROPERTY_SPEC
    if variant_profile == INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE:
        return _INVESTMENT_PROPERTY_REPORTING_PERIOD_GENERAL_SPEC
    raise _error("investment-property variant profile drifted")


def _validate_investment_property_result(value: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("investment-property graph result fields drifted")
    if (
        value["format_version"] != spec["format_version"]
        or value["family_id"] != spec["family_id"]
        or value["claim_boundary"] != spec["claim_boundary"]
        or not same_typed_json_v1(value["safety"], spec["safety"])
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
    ):
        raise _error("investment-property graph identity or authority drifted")
    complete_count = len(value["regions"])
    comparison_count = sum(
        len(region.get("comparison_controls", [])) for region in value["regions"]
    )
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
        "comparison_region_count": comparison_count,
        "complete_region_count": complete_count,
        "near_region_count": len(value["near_regions"]),
        "owner_candidate_count": complete_count + len(value["near_regions"]),
    }
    if (
        value["status"] != expected_status
        or not same_typed_json_v1(value["uniqueness"], expected_uniqueness)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
    ):
        raise _error("investment-property graph metrics or uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != spec["id_prefix"] + canonical_json_sha256_v1(material):
        raise _error("investment-property graph identity drifted")
    return canonical_clone_v1(value)


def build_investment_property_variant_graph_document_v1(
    pages: Any, *, variant_profile: str = CURRENT_VARIANT_PROFILE
) -> dict[str, Any]:
    """Enumerate current and retained comparative investment-property regions."""

    spec = _investment_property_spec(variant_profile)
    normalized_pages = _pages(pages)
    owners = [
        line
        for page in normalized_pages
        for line in page["lines"]
        if _is_owner_line(line, spec) and _owner_layout_eligible(line, page, spec)
    ]
    regions: list[dict[str, Any]] = []
    near_regions: list[dict[str, Any]] = []
    for owner in owners:
        candidates = _investment_property_owner_candidates(owner, normalized_pages, spec)
        complete = [candidate for candidate in candidates if candidate["complete"]]
        incomplete = [candidate for candidate in candidates if not candidate["complete"]]
        near_regions.extend(incomplete)
        if not complete:
            continue
        ranked = [candidate for candidate in complete if candidate["period_end"] is not None]
        if ranked:
            newest = max(tuple(candidate["period_end"]) for candidate in ranked)
            current = [
                candidate for candidate in complete if tuple(candidate["period_end"]) == newest
            ]
            comparisons = [candidate for candidate in complete if candidate not in current]
        else:
            current = complete
            comparisons = []
        for candidate in current:
            candidate["comparison_controls"] = canonical_clone_v1(comparisons)
            candidate["period_selection_rule"] = (
                "LATEST_EXPLICIT_PERIOD_END_WITHIN_OWNER"
                if ranked
                else "NO_EXPLICIT_COMPARATIVE_PERIOD_REGION"
            )
            regions.append(candidate)
    material = {
        "claim_boundary": spec["claim_boundary"],
        "family_id": spec["family_id"],
        "format_version": spec["format_version"],
        "metrics": {
            "comparison_region_count": sum(
                len(region["comparison_controls"]) for region in regions
            ),
            "complete_region_count": len(regions),
            "near_region_count": len(near_regions),
            "owner_candidate_count": len(regions) + len(near_regions),
        },
        "near_regions": near_regions,
        "regions": regions,
        "safety": canonical_clone_v1(spec["safety"]),
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
    return _validate_investment_property_result(
        {
            **material,
            "result_id": spec["id_prefix"] + canonical_json_sha256_v1(material),
        },
        spec,
    )


def validate_tangible_fixed_assets_variant_graph_replay_v1(
    value: Any,
    pages: Any,
    *,
    variant_profile: str = CURRENT_VARIANT_PROFILE,
) -> dict[str, Any]:
    """Rebuild the graph from the complete PDF and require typed equality."""

    spec = _tangible_spec(variant_profile)
    supplied = _validate_result(value, spec)
    rebuilt = build_tangible_fixed_assets_variant_graph_document_v1(
        pages, variant_profile=variant_profile
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("tangible-fixed-assets graph does not replay exactly")
    return supplied


def validate_leased_fixed_assets_variant_graph_replay_v1(
    value: Any,
    pages: Any,
    *,
    variant_profile: str = CURRENT_VARIANT_PROFILE,
) -> dict[str, Any]:
    """Rebuild the leased-asset graph from the complete PDF."""

    spec = _leased_spec(variant_profile)
    supplied = _validate_result(value, spec)
    rebuilt = build_leased_fixed_assets_variant_graph_document_v1(
        pages, variant_profile=variant_profile
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("leased-fixed-assets graph does not replay exactly")
    return supplied


def validate_intangible_fixed_assets_variant_graph_replay_v1(
    value: Any,
    pages: Any,
    *,
    variant_profile: str = CURRENT_VARIANT_PROFILE,
) -> dict[str, Any]:
    """Rebuild the intangible-asset graph from the complete PDF."""

    spec = _intangible_spec(variant_profile)
    supplied = _validate_result(value, spec)
    rebuilt = build_intangible_fixed_assets_variant_graph_document_v1(
        pages, variant_profile=variant_profile
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("intangible-fixed-assets graph does not replay exactly")
    return supplied


def validate_investment_property_variant_graph_replay_v1(
    value: Any,
    pages: Any,
    *,
    variant_profile: str = CURRENT_VARIANT_PROFILE,
) -> dict[str, Any]:
    """Rebuild the investment-property graph from the complete PDF."""

    spec = _investment_property_spec(variant_profile)
    supplied = _validate_investment_property_result(value, spec)
    rebuilt = build_investment_property_variant_graph_document_v1(
        pages, variant_profile=variant_profile
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("investment-property graph does not replay exactly")
    return supplied
