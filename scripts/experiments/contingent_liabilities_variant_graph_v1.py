"""Bank-blind variant graph for contingent liabilities and commitments."""

from __future__ import annotations

import importlib.util
import itertools
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "CONTINGENT_LIABILITIES_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CONTINGENT_LIABILITIES_AND_COMMITMENTS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_PAIR_FIRST_OWNER_GROUP_CHILD_"
    "PERIOD_UNIT_NUMERIC_AND_ACCOUNTING_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_"
    "MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "financial_statement_summary_can_impersonate_detailed_note": False,
    "fresh_vietocr_transformer_text_required": True,
    "geographic_or_risk_table_can_accept": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "sibling_order_required_for_matching": False,
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


class ContingentLiabilitiesVariantGraphV1Error(ValueError):
    """The complete-PDF input or contingent-liabilities graph drifted."""


def _error(message: str) -> ContingentLiabilitiesVariantGraphV1Error:
    return ContingentLiabilitiesVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_contingent_liabilities"
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
        ("nghia vu no tiem" in value and "cam ket dua ra" in value)
        or value in {"cac cam ket ngoai bang", "cam ket ngoai bang"}
        or (
            "hoat dong ngoai bang" in value
            and "rui ro" in value
            and ("dang ke" in value or "trong yeu" in value)
        )
    )


def _negative_family(text: str) -> bool:
    value = _strip(text)
    return (
        "khu vuc dia ly" in value
        or "nhay cam voi lai suat" in value
        or "phan loai no cho cac cam ket" in value
        or "chi tieu ngoai bao cao tinh hinh tai chinh" in value
        or "chi tieu ngoai bang can doi ke toan" in value
    )


def _role(text: str) -> str | None:
    value = _strip(text)
    if "bao lanh vay von" in value:
        return "GUARANTEE_LOAN"
    if "bao lanh thanh toan" in value:
        return "GUARANTEE_PAYMENT"
    if "bao lanh thuc hien" in value:
        return "GUARANTEE_PERFORMANCE"
    if "bao lanh du thau" in value:
        return "GUARANTEE_BID"
    if "bao lanh" in value and ("khac" in value or "con lai" in value):
        return "GUARANTEE_OTHER"
    if "cam ket mua ngoai te" in value:
        return "FX_BUY"
    if "cam ket ban ngoai te" in value:
        return "FX_SELL"
    if "hoan doi" in value and ("nhan" in value or "mua" in value):
        return "SWAP_RECEIVE_OR_BUY"
    if "hoan doi" in value and ("tra" in value or "ban" in value):
        return "SWAP_PAY_OR_SELL"
    if "cam ket giao dich hoan doi" in value:
        return "SWAP_PARENT"
    if "cam ket giao dich hoi doai" in value or "cac cam ket giao dich hoi doai" in value:
        return "FX_PARENT"
    if "thu tin dung" in value or "nghiep vu l c" in value or "nghiep vu lc" in value:
        return "LETTER_OF_CREDIT"
    if "mua ban giay to co gia" in value:
        return "VALUABLE_PAPER_COMMITMENT"
    if value.startswith("nghia vu no tiem"):
        return "CONTINGENT_GROUP"
    if value == "cac cam ket dua ra":
        return "COMMITMENT_GROUP"
    if value in {"bao lanh khac", "cam ket bao lanh khac"}:
        return "GUARANTEE_OTHER"
    if value in {"cam ket khac", "cac cam ket khac"}:
        return "OTHER_COMMITMENTS"
    return None


def _axis_role(text: str) -> str | None:
    # Dates often start with a number; stripping an enumerator would turn
    # ``31 12 2025`` into ``2025`` and destroy the period axis.
    value = text.strip()
    if "31 12 2025" in value or "31 thang 12" in value or "nam 2025" in value:
        return "COMPARATIVE_AXIS"
    if (
        "30 6 2026" in value
        or "30 06 2026" in value
        or "31 3 2026" in value
        or "31 thang 3" in value
        or "30 thang 6" in value
        or "nam 2026" in value
    ):
        return "CURRENT_AXIS"
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    return None


def _region(page: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    support = _support()
    roles: list[str] = []
    axes: list[str] = []
    events = [support._line_ref(owner, "FAMILY_OWNER")]
    numeric_count = 0
    negative_controls = []
    for index, line in enumerate(page["lines"]):
        text = line["normalized_text"]
        if _negative_family(text):
            negative_controls.append(support._line_ref(line, "NEGATIVE_FAMILY_OWNER"))
        joined_two = (
            f"{text} {page['lines'][index + 1]['normalized_text']}"
            if index + 1 < len(page["lines"])
            else text
        )
        joined_three = (
            f"{joined_two} {page['lines'][index + 2]['normalized_text']}"
            if index + 2 < len(page["lines"])
            else joined_two
        )
        role = _role(text) or _role(joined_two) or _role(joined_three)
        if role is not None:
            roles.append(role)
            events.append(support._line_ref(line, role))
        axis = _axis_role(text)
        if axis is None and index + 1 < len(page["lines"]):
            axis = _axis_role(f"{text} {page['lines'][index + 1]['normalized_text']}")
        if axis is not None:
            axes.append(axis)
            events.append(support._line_ref(line, axis))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    observed_roles = list(dict.fromkeys(roles))
    observed_axes = list(dict.fromkeys(axes))
    core = {
        "GUARANTEE_LOAN",
        "FX_PARENT",
        "LETTER_OF_CREDIT",
        "GUARANTEE_OTHER",
        "OTHER_COMMITMENTS",
    }
    child_depth = bool(
        set(observed_roles)
        & {
            "FX_BUY",
            "FX_SELL",
            "SWAP_RECEIVE_OR_BUY",
            "SWAP_PAY_OR_SELL",
            "SWAP_PARENT",
            "GUARANTEE_PAYMENT",
            "GUARANTEE_PERFORMANCE",
            "GUARANTEE_BID",
            "VALUABLE_PAPER_COMMITMENT",
        }
    )
    two_group_variant = {"CONTINGENT_GROUP", "COMMITMENT_GROUP"}.issubset(observed_roles)
    required_axes = {"CURRENT_AXIS", "COMPARATIVE_AXIS", "UNIT_AXIS"}
    complete = (
        not negative_controls
        and len(core & set(observed_roles)) >= 3
        and (child_depth or two_group_variant)
        and required_axes.issubset(observed_axes)
        and numeric_count >= 8
    )
    anchors = ["FAMILY_OWNER", *sorted(core & set(observed_roles))]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": page["lines"][-1]["global_ordinal"],
        "events": events,
        "layout": {
            "child_depth_observed": child_depth,
            "observed_axis_roles": observed_axes,
            "observed_source_roles": observed_roles,
            "sibling_order_is_semantic": False,
            "two_group_variant_observed": two_group_variant,
        },
        "negative_family_controls": negative_controls,
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "FAMILY_OWNER"),
        "page_span": [page["page_sequence"], page["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": page["lines"][0]["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("contingent-liabilities graph fields drifted")
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
        raise _error("contingent-liabilities graph identity drifted")
    count = len(value["regions"])
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH" if count == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
    )
    uniqueness = (
        "UNIQUE_FULL_MATCH"
        if count == 1
        else "NO_FULL_MATCH"
        if count == 0
        else "MULTIPLE_FULL_MATCHES"
    )
    if value["status"] != expected_status or value["uniqueness"] != {
        "complete_region_count": count,
        "status": uniqueness,
    }:
        raise _error("contingent-liabilities disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "clvgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("contingent-liabilities graph ID drifted")
    return canonical_clone_v1(value)


def build_contingent_liabilities_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    candidates = []
    for page in parsed:
        owners = []
        for index, line in enumerate(page["lines"]):
            text = line["normalized_text"]
            joined = (
                f"{text} {page['lines'][index + 1]['normalized_text']}"
                if index + 1 < len(page["lines"])
                else text
            )
            if _owner(text) or _owner(joined):
                owners.append(line)
        for owner in owners:
            candidates.append(_region(page, owner))
    # A heading repeated in prose on the same page is one physical region, not a second candidate.
    by_page: dict[int, dict[str, Any]] = {}
    for candidate in candidates:
        page = candidate["owner"]["page_sequence"]
        previous = by_page.get(page)
        if previous is None or (candidate["complete"] and not previous["complete"]):
            by_page[page] = candidate
    candidates = list(by_page.values())
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
            "status": "UNIQUE_FULL_MATCH"
            if len(regions) == 1
            else "NO_FULL_MATCH"
            if not regions
            else "MULTIPLE_FULL_MATCHES",
        },
    }
    return _validate(
        {**material, "result_id": "clvgv1:graph:" + canonical_json_sha256_v1(material)}
    )
