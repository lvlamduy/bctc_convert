"""Bank-blind variant graph for cash-and-cash-equivalent disclosures."""

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

FORMAT_VERSION = "CASH_EQUIVALENTS_VARIANT_GRAPH_DOCUMENT_V1"
BASELINE_VARIANT_PROFILE = "HISTORICAL_BASELINE_V1"
EXTENDED_VARIANT_PROFILE = "GENERIC_CENTRAL_BANK_NAMES_AND_OCR_NOISE_V2"
_VARIANT_PROFILES = {BASELINE_VARIANT_PROFILE, EXTENDED_VARIANT_PROFILE}
_FIELDS = {
    "claim_boundary",
    "format_version",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_CLAIM = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_CASH_EQUIVALENTS_OWNER_CASH_"
    "CENTRAL_BANK_INTERBANK_OPTIONAL_SECURITIES_PERIOD_UNIT_AND_PRINTED_TOTAL_"
    "STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "blank_cell_interpreted_as_zero": False,
    "cash_flow_beginning_or_ending_balance_alone_can_accept": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_interbank_split_and_securities_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "policy_text_alone_can_accept": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_can_accept": False,
}


class CashEquivalentsVariantGraphV1Error(ValueError):
    """The semantic input or cash-equivalents graph drifted."""


def _error(message: str) -> CashEquivalentsVariantGraphV1Error:
    return CashEquivalentsVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_cash_equivalents"
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


def _owner_text(text: str) -> bool:
    value = _strip(text)
    return value in {
        "tien va cac khoan tuong duong tien",
        "tien va cac khoan tuong duong tien gom co",
    }


def _extended(profile: str) -> bool:
    if profile not in _VARIANT_PROFILES:
        raise _error("cash-equivalents variant profile is unsupported")
    return profile == EXTENDED_VARIANT_PROFILE


def _within_one_edit(left: str, right: str) -> bool:
    """Return whether two short OCR tokens differ by at most one edit."""

    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    cursor = 0
    for index, character in enumerate(right):
        if cursor < len(left) and left[cursor] == character:
            cursor += 1
        elif index - cursor > 0:
            return False
    return True


def _central_bank_deposit(value: str, profile: str) -> bool:
    baseline = (
        value.startswith("tien gui tai nhnn")
        or value.startswith("tien gui tai ngan hang nha nuoc")
        or value.startswith("tien gui thanh toan tai ngan hang nha nuoc")
    )
    if baseline or not _extended(profile):
        return baseline
    if value.startswith("tien gui tai ngan hang trung uong"):
        return True
    words = value.split()
    return (
        len(words) >= 4
        and words[:3] == ["tien", "gui", "tai"]
        and _within_one_edit(words[3], "nhnn")
    )


def _role(text: str, profile: str = BASELINE_VARIANT_PROFILE) -> str | None:
    value = _strip(text)
    _extended(profile)
    if len(value.split()) > 24:
        return None
    if _owner_text(value):
        return "OWNER"
    if value.startswith("tien mat") or value.startswith(
        "tien va cac khoan tuong duong tien tai quy"
    ):
        return "CASH_AND_PRECIOUS_METALS"
    if _central_bank_deposit(value, profile):
        return "CENTRAL_BANK_DEPOSIT"
    if "tctd" in value or "to chuc tin dung" in value:
        if "khong ky han" in value or "thanh toan" in value:
            return "INTERBANK_DEMAND"
        if ("co ky han" in value or "ky han goc" in value) and (
            "khong qua 3" in value or "khong qua ba" in value
        ):
            return "INTERBANK_TERM_UP_TO_3_MONTHS"
        return "INTERBANK_GENERAL"
    if value.startswith("chung khoan") and (
        "khong qua 3" in value
        or "khong qua ba" in value
        or "co thoi han thu hoi hoac dao han" in value
        or value.startswith("chung khoan dau tu")
    ):
        return "SECURITIES_UP_TO_3_MONTHS"
    return None


def _region(
    lines: Sequence[Mapping[str, Any]],
    start: int,
    profile: str = BASELINE_VARIANT_PROFILE,
) -> dict[str, Any]:
    support = _support()
    owner = lines[start]
    window = [line for line in lines if line["page_sequence"] == owner["page_sequence"]]
    roles: list[str] = []
    events = [support._line_ref(owner, "OWNER")]
    period_count = 0
    unit_count = 0
    numeric_count = 0
    for index, line in enumerate(window):
        text = line["normalized_text"]
        axis = support._axis_role(text)
        if axis:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
            continue
        role = _role(text, profile)
        if not _extended(profile):
            # Preserve the exact historical V1 graph and its persisted IDs.
            if role is None and index + 1 < len(window):
                following = window[index + 1]["normalized_text"]
                if not support._NUMBER.fullmatch(following):
                    role = _role(f"{text} {following}", profile)
        else:
            continuation_candidate = role is None or (
                role == "INTERBANK_GENERAL"
                and _strip(text).endswith(("khong", "khong qua", "ky han"))
            )
            if continuation_candidate and index + 1 < len(window):
                for following_line in window[index + 1 : index + 4]:
                    following = following_line["normalized_text"]
                    if support._NUMBER.fullmatch(following):
                        continue
                    combined_role = _role(f"{text} {following}", profile)
                    if combined_role is not None:
                        role = combined_role
                    break
        if role and role != "OWNER":
            roles.append(role)
            events.append(support._line_ref(line, role))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    observed = list(dict.fromkeys(roles))
    interbank = any(role.startswith("INTERBANK_") for role in observed)
    required = {"CASH_AND_PRECIOUS_METALS", "CENTRAL_BANK_DEPOSIT"}
    complete = (
        required <= set(observed)
        and interbank
        and period_count >= 2
        and unit_count >= 1
        and numeric_count >= 7
    )
    anchors = [
        "OWNER",
        "CASH_AND_PRECIOUS_METALS",
        "CENTRAL_BANK_DEPOSIT",
        "INTERBANK",
        "PERIOD_AXIS",
        "UNIT_AXIS",
    ]
    presentation = (
        "CASH_FLOW_TOTAL_BEFORE_COMPONENTS"
        if _strip(owner["normalized_text"]).endswith("gom co")
        else "DETAIL_NOTE_COMPONENTS_THEN_TRAILING_TOTAL"
    )
    end = window[-1]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": end["global_ordinal"],
        "events": events,
        "layout": {
            "interbank_presentation": (
                "DEMAND_AND_TERM_SPLIT"
                if {"INTERBANK_DEMAND", "INTERBANK_TERM_UP_TO_3_MONTHS"} <= set(observed)
                else "GENERAL_OR_COMBINED"
            ),
            "observed_roles": observed,
            "period_axis_line_count": period_count,
            "presentation": presentation,
            "securities_row_present": "SECURITIES_UP_TO_3_MONTHS" in observed,
            "unit_axis_line_count": unit_count,
        },
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "OWNER"),
        "page_span": [owner["page_sequence"], owner["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": window[0]["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "demand_term_split_region_count": sum(
            item["layout"]["interbank_presentation"] == "DEMAND_AND_TERM_SPLIT" for item in regions
        ),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "securities_optional_region_count": sum(
            item["layout"]["securities_row_present"] for item in regions
        ),
        "total_before_components_region_count": sum(
            item["layout"]["presentation"] == "CASH_FLOW_TOTAL_BEFORE_COMPONENTS"
            for item in regions
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("cash-equivalents graph fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["regions"]) is not list
        or type(value["near_regions"]) is not list
        or not same_typed_json_v1(
            value["metrics"], _metrics(value["regions"], value["near_regions"])
        )
    ):
        raise _error("cash-equivalents graph identity drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    expected_unique = {
        "complete_region_count": count,
        "status": "UNIQUE_FULL_MATCH" if count == 1 else "NOT_UNIQUE_FULL_MATCH",
    }
    if value["status"] != expected_status or not same_typed_json_v1(
        value["uniqueness"], expected_unique
    ):
        raise _error("cash-equivalents uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "cevgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("cash-equivalents graph ID drifted")
    return canonical_clone_v1(value)


def build_cash_equivalents_variant_graph_document_v1(
    pages: Any, *, variant_profile: str = BASELINE_VARIANT_PROFILE
) -> dict[str, Any]:
    _extended(variant_profile)
    try:
        parsed = _support()._pages(pages)
    except Exception as exc:
        raise _error(str(exc)) from exc
    lines = _support()._flatten(parsed)
    candidates = [
        _region(lines, index, variant_profile)
        for index, line in enumerate(lines)
        if _owner_text(line["normalized_text"])
    ]
    regions = [item for item in candidates if item["complete"]]
    near = [item for item in candidates if not item["complete"]]
    material = {
        "claim_boundary": _CLAIM,
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
    return _validate(
        {**material, "result_id": "cevgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_cash_equivalents_variant_graph_replay_v1(
    value: Any,
    pages: Any,
    *,
    variant_profile: str = BASELINE_VARIANT_PROFILE,
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_cash_equivalents_variant_graph_document_v1(
        pages, variant_profile=variant_profile
    )
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("cash-equivalents graph does not replay exactly")
    return supplied
