"""Bank-blind variant graph for detailed corporate-income-tax reconciliations."""

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

FORMAT_VERSION = "INCOME_TAX_VARIANT_GRAPH_DOCUMENT_V1"
BASELINE_VARIANT_PROFILE = "HISTORICAL_BASELINE_V1"
EXTENDED_VARIANT_PROFILE = "GENERIC_ANNUAL_AND_INTERIM_V2"
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
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_DETAILED_CORPORATE_INCOME_TAX_"
    "RECONCILIATION_PROFIT_BEFORE_TAX_ADJUSTMENTS_TAXABLE_INCOME_CURRENT_TAX_"
    "AND_OPTIONAL_COMPONENT_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "blank_cell_interpreted_as_zero": False,
    "complete_pdf_region_enumeration_required": True,
    "dash_cell_may_be_zero_only_after_source_or_pixel_verification": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_tax_components_supported": True,
    "pair_search_exhausted_before_larger_combinations": True,
    "profit_before_tax_must_precede_taxable_income": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_aggregate_or_tax_obligation_rollforward_can_accept": False,
    "text_similarity_alone_can_accept": False,
}


class IncomeTaxVariantGraphV1Error(ValueError):
    """The semantic input or income-tax graph drifted."""


def _error(message: str) -> IncomeTaxVariantGraphV1Error:
    return IncomeTaxVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_income_tax"
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
    return _support()._strip_enumerator(text).strip()


def _extended(profile: str) -> bool:
    if profile not in _VARIANT_PROFILES:
        raise _error("income-tax variant profile is unsupported")
    return profile == EXTENDED_VARIANT_PROFILE


def _profit_before_tax(text: str, profile: str = BASELINE_VARIANT_PROFILE) -> bool:
    value = _strip(text)
    if not _extended(profile):
        return (
            "loi nhuan" in value
            and "truoc thue" in value
            and ("tndn" in value or "ke toan" in value)
        )
    words = value.split()
    return (
        len(words) <= 12
        and "loi nhuan" in value
        and "truoc thue" in value
        and (
            "tndn" in value
            or "ke toan" in value
            or value in {"loi nhuan truoc thue", "tong loi nhuan truoc thue"}
        )
    )


def _role(text: str, profile: str = BASELINE_VARIANT_PROFILE) -> str | None:
    value = _strip(text)
    extended = _extended(profile)
    if len(value.split()) > 30:
        return None
    if _profit_before_tax(value, profile):
        return "PROFIT_BEFORE_TAX"
    if (
        "thu nhap khong chiu thue" in value
        or ("thu nhap tu" in value and "khong chiu thue" in value)
        or (
            extended
            and (
                ("co tuc" in value and "khong chiu thue" in value)
                or "thu nhap tu gop von mua co phan" in value
            )
        )
    ):
        return "NON_TAXABLE_INCOME"
    if "chi phi khong duoc khau tru" in value or (
        extended and "chi phi khong duoc" in value and "duoc tru" in value
    ):
        return "NON_DEDUCTIBLE_EXPENSE"
    if value.startswith("dieu chinh lien quan") or (
        extended and ("dieu chinh hop nhat" in value or "but toan dieu chinh hop nhat" in value)
    ):
        return "CONSOLIDATION_ADJUSTMENT"
    if value.startswith("cac khoan dieu chinh khac"):
        return "OTHER_TAXABLE_INCOME_ADJUSTMENT"
    if value.startswith("thu nhap chiu thue"):
        return "TAXABLE_INCOME"
    if (
        "theo thue suat hien hanh" in value
        or "tinh tren thu nhap chiu thue" in value
        or (
            extended
            and ("theo thue suat ap dung" in value or "chi phi thue tndn theo thue suat" in value)
        )
    ):
        return "CURRENT_TAX_AT_RATE"
    if "dieu chinh" in value and (
        "cac ky truoc" in value or "cac nam truoc" in value or "nam truoc" in value
    ):
        return "PRIOR_PERIOD_TAX_ADJUSTMENT"
    if (
        value.startswith("tong chi phi thue tndn hien hanh")
        or value.startswith("chi phi thue tndn phai tra trong ky")
        or (extended and value.startswith("chi phi thue tndn trong nam"))
    ):
        return "CURRENT_TAX_TOTAL"
    if "chi phi thue tndn hien hanh rieng ngan hang" in value or (
        extended
        and (
            ("thue tndn cua ngan hang" in value and "chi nhanh" not in value)
            or ("chi phi thue tndn hien hanh" in value and "ngan hang" in value)
        )
    ):
        return "CURRENT_TAX_BANK"
    if "chi phi thue tndn chi nhanh nuoc ngoai" in value or (
        extended and "thue tndn" in value and "chi nhanh nuoc ngoai" in value
    ):
        return "CURRENT_TAX_FOREIGN_BRANCH"
    if "chi phi thue tndn cua cac cong ty con" in value or (
        extended and "thue tndn" in value and ("cong ty con" in value or "toan he thong" in value)
    ):
        return "CURRENT_TAX_SUBSIDIARIES"
    if "chi phi" in value and "thue tndn hoan lai" in value:
        return "DEFERRED_TAX_COMPONENT"
    if value.startswith("chi phi thue tndn") and any(
        token in value for token in ("i+ii", "i ii", "iv", "v")
    ):
        return "TOTAL_TAX_EXPENSE"
    if value.startswith("chi phi thue thu nhap hien hanh"):
        return "CURRENT_TAX_EXPENSE_PARENT"
    if value == "nam hien hanh":
        return "CURRENT_TAX_EXPENSE_CHILD"
    if value.startswith("chi phi") and "thu nhap" in value and "thue thu nhap hoan lai" in value:
        return "DEFERRED_TAX_EXPENSE_CHILD"
    if value.startswith("chi phi") and "thue thu nhap hoan lai" in value:
        return "DEFERRED_TAX_EXPENSE_PARENT"
    if value == "chi phi thue thu nhap":
        return "TOTAL_TAX_EXPENSE"
    if value.startswith("dieu chinh khac"):
        return "OTHER_CURRENT_TAX_ADJUSTMENT"
    return None


def _page_window(lines: Sequence[Mapping[str, Any]], start: int) -> list[Mapping[str, Any]]:
    page = lines[start]["page_sequence"]
    return [line for line in lines if line["page_sequence"] == page]


def _region(
    lines: Sequence[Mapping[str, Any]], start: int, profile: str = BASELINE_VARIANT_PROFILE
) -> dict[str, Any]:
    support = _support()
    window = _page_window(lines, start)
    owner = lines[start]
    events = []
    roles: list[str] = []
    ordinals: dict[str, int] = {}
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
        if role is None and index + 1 < len(window):
            following = window[index + 1]["normalized_text"]
            if not support._NUMBER.fullmatch(following):
                role = _role(f"{text} {following}", profile)
        if role:
            roles.append(role)
            ordinals.setdefault(role, line["global_ordinal"])
            events.append(support._line_ref(line, role))
        if support._NUMBER.fullmatch(text) and line["bbox"][0] > 400:
            numeric_count += 1
    observed = list(dict.fromkeys(roles))
    extended = _extended(profile)
    required = (
        {"PROFIT_BEFORE_TAX", "TAXABLE_INCOME"}
        if extended
        else {"PROFIT_BEFORE_TAX", "NON_DEDUCTIBLE_EXPENSE", "TAXABLE_INCOME"}
    )
    has_adjustment = (
        any(
            role in observed
            for role in (
                "CONSOLIDATION_ADJUSTMENT",
                "NON_DEDUCTIBLE_EXPENSE",
                "NON_TAXABLE_INCOME",
                "OTHER_TAXABLE_INCOME_ADJUSTMENT",
            )
        )
        if extended
        else True
    )
    has_tax = any(
        role in observed
        for role in (
            "CURRENT_TAX_AT_RATE",
            "CURRENT_TAX_BANK",
            "CURRENT_TAX_EXPENSE_PARENT",
            "CURRENT_TAX_TOTAL",
            "TOTAL_TAX_EXPENSE",
        )
    )
    order_ok = (
        "PROFIT_BEFORE_TAX" in ordinals
        and "TAXABLE_INCOME" in ordinals
        and ordinals["PROFIT_BEFORE_TAX"] < ordinals["TAXABLE_INCOME"]
    )
    complete = (
        required <= set(observed)
        and has_adjustment
        and has_tax
        and order_ok
        and period_count >= 2
        and unit_count >= 1
        and numeric_count >= 10
    )
    anchors = [
        "PROFIT_BEFORE_TAX",
        "TAXABLE_INCOME",
        "NON_DEDUCTIBLE_EXPENSE",
        "CURRENT_TAX",
        "PERIOD_AXIS",
        "UNIT_AXIS",
    ]
    q1 = "3 thang" in " ".join(line["normalized_text"] for line in window[:24])
    presentation = (
        "FULL_CURRENT_DEFERRED_AND_FIVE_COMPONENT_TAX_RECONCILIATION"
        if {"CURRENT_TAX_BANK", "CURRENT_TAX_SUBSIDIARIES", "DEFERRED_TAX_COMPONENT"}
        <= set(observed)
        else "CURRENT_TAX_RECONCILIATION_WITH_OPTIONAL_ADJUSTMENTS"
    )
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": window[-1]["global_ordinal"],
        "events": events,
        "layout": {
            "observed_roles": observed,
            "period_axis_line_count": period_count,
            "presentation": presentation,
            "profit_before_tax_precedes_taxable_income": order_ok,
            "q1_period_context": q1,
            "unit_axis_line_count": unit_count,
        },
        "numeric_line_count": numeric_count,
        "owner": support._line_ref(owner, "PROFIT_BEFORE_TAX"),
        "page_span": [owner["page_sequence"], owner["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": window[0]["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "full_component_variant_region_count": sum(
            item["layout"]["presentation"].startswith("FULL_") for item in regions
        ),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "q1_axis_region_count": sum(item["layout"]["q1_period_context"] for item in regions),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("income-tax graph fields drifted")
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
        raise _error("income-tax graph identity drifted")
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
        raise _error("income-tax uniqueness drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "itvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("income-tax graph ID drifted")
    return canonical_clone_v1(value)


def build_income_tax_variant_graph_document_v1(
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
        if _profit_before_tax(line["normalized_text"], variant_profile)
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
        {**material, "result_id": "itvgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_income_tax_variant_graph_replay_v1(
    value: Any, pages: Any, *, variant_profile: str = BASELINE_VARIANT_PROFILE
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_income_tax_variant_graph_document_v1(pages, variant_profile=variant_profile)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("income-tax graph does not replay exactly")
    return supplied
