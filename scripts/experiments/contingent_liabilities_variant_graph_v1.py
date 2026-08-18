"""Bank-blind variant graph for contingent liabilities and commitments."""

from __future__ import annotations

import importlib.util
import itertools
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import extract_reporting_year_axis_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "CONTINGENT_LIABILITIES_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "CONTINGENT_LIABILITIES_AND_COMMITMENTS"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_PAIR_FIRST_LOCAL_OWNER_TABLE_"
    "OPTIONAL_ONE_PAGE_CONTINUATION_GROUP_CHILD_PERIOD_UNIT_NUMERIC_AND_"
    "ACCOUNTING_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
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
    "single_next_page_continuation_supported": True,
    "sibling_order_required_for_matching": False,
    "table_evidence_scoped_from_owner_to_next_numbered_note": True,
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
        (
            ("nghia vu no tiem" in value or "nghia vu tiem" in value)
            and ("cam ket dua ra" in value or "cac cam ket" in value)
        )
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
    if "cac khoan bao lanh" in value:
        return "GUARANTEE_GROUP"
    if "cam ket thanh toan" in value:
        return "PAYMENT_COMMITMENT_GROUP"
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
    if "thu tin dung" in value or ("cam ket" in value and "nghiep vu l" in value):
        return "LETTER_OF_CREDIT"
    if "mua ban giay to co gia" in value:
        return "VALUABLE_PAPER_COMMITMENT"
    if value.startswith("nghia vu") and "tiem" in value:
        return "CONTINGENT_GROUP"
    if value == "cac cam ket dua ra":
        return "COMMITMENT_GROUP"
    if value in {"bao lanh khac", "cam ket bao lanh khac"}:
        return "GUARANTEE_OTHER"
    if value in {"cam ket khac", "cac cam ket khac"}:
        return "OTHER_COMMITMENTS"
    return None


def _axis_role(text: str) -> str | None:
    value = _strip(text)
    if "trieu dong" in value or "trieu vnd" in value:
        return "UNIT_AXIS"
    if value in {"so cuoi nam", "so cuoi ky"}:
        return "CURRENT_AXIS"
    if value in {"so dau nam", "so dau ky"}:
        return "COMPARATIVE_AXIS"
    return None


def _numbered_note_marker(line: Mapping[str, Any]) -> bool:
    return bool(
        line["bbox"][0] < 350
        and re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3}){0,2}\.?", line["normalized_text"].strip())
    )


def _region_lines(
    pages: list[dict[str, Any]],
    page_index: int,
    owner_index: int,
    *,
    include_next_page: bool,
) -> list[dict[str, Any]]:
    selected = [pages[page_index]["lines"][owner_index]]
    current = pages[page_index]["lines"]
    for line in current[owner_index + 1 :]:
        if _numbered_note_marker(line):
            break
        selected.append(line)
    if include_next_page and page_index + 1 < len(pages):
        following = pages[page_index + 1]
        if following["page_sequence"] == pages[page_index]["page_sequence"] + 1:
            for line in following["lines"]:
                if _numbered_note_marker(line):
                    break
                selected.append(line)
    return selected


def _pre_owner_context(
    pages: list[dict[str, Any]], page_index: int, owner_index: int
) -> list[dict[str, Any]]:
    owner = pages[page_index]["lines"][owner_index]
    if _numbered_note_marker(owner):
        return []
    lines = pages[page_index]["lines"]
    start = 0
    for index in range(owner_index - 1, -1, -1):
        if _numbered_note_marker(lines[index]):
            start = index + 1
            break
    return lines[start:owner_index]


def _region(
    pages: list[dict[str, Any]],
    page_index: int,
    owner_index: int,
    *,
    include_next_page: bool = False,
) -> dict[str, Any]:
    support = _support()
    owner = pages[page_index]["lines"][owner_index]
    region_lines = _region_lines(
        pages, page_index, owner_index, include_next_page=include_next_page
    )
    roles: list[str] = []
    axes: list[str] = []
    events = [support._line_ref(owner, "FAMILY_OWNER")]
    numeric_count = 0
    negative_controls = []
    for line in [*_pre_owner_context(pages, page_index, owner_index), *region_lines]:
        if _negative_family(line["normalized_text"]):
            negative_controls.append(support._line_ref(line, "NEGATIVE_FAMILY_OWNER"))
    for index, line in enumerate(region_lines):
        text = line["normalized_text"]
        joined_two = (
            f"{text} {region_lines[index + 1]['normalized_text']}"
            if index + 1 < len(region_lines)
            else text
        )
        joined_three = (
            f"{joined_two} {region_lines[index + 2]['normalized_text']}"
            if index + 2 < len(region_lines)
            else joined_two
        )
        role = _role(text) or _role(joined_two) or _role(joined_three)
        if role is not None:
            roles.append(role)
            events.append(support._line_ref(line, role))
        axis = _axis_role(text)
        if axis is None and index + 1 < len(region_lines):
            axis = _axis_role(f"{text} {region_lines[index + 1]['normalized_text']}")
        if axis is not None:
            axes.append(axis)
            events.append(support._line_ref(line, axis))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    for page_sequence in dict.fromkeys(line["page_sequence"] for line in region_lines):
        local_lines = [line for line in region_lines if line["page_sequence"] == page_sequence]
        line_by_index = {line["source_line_index"]: line for line in local_lines}
        year_axis, _year_axis_mode = extract_reporting_year_axis_v1(local_lines)
        for item in year_axis:
            axis = "CURRENT_AXIS" if item["role"] == "CURRENT_PERIOD" else "COMPARATIVE_AXIS"
            if axis not in axes:
                axes.append(axis)
                line = line_by_index[item["evidence_source_line_indices"][0]]
                events.append(support._line_ref(line, axis))
    observed_roles = list(dict.fromkeys(roles))
    observed_axes = list(dict.fromkeys(axes))
    observed_role_set = set(observed_roles)
    child_depth = bool(
        observed_role_set
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
            "GUARANTEE_GROUP",
            "PAYMENT_COMMITMENT_GROUP",
        }
    )
    two_group_variant = {"CONTINGENT_GROUP", "COMMITMENT_GROUP"}.issubset(observed_role_set)
    required_axes = {"CURRENT_AXIS", "COMPARATIVE_AXIS", "UNIT_AXIS"}
    complete = (
        not negative_controls
        and len(observed_role_set) >= 2
        and required_axes.issubset(observed_axes)
        and numeric_count >= 4
    )
    anchors = list(dict.fromkeys(["FAMILY_OWNER", *sorted(observed_role_set)]))
    result = {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": region_lines[-1]["global_ordinal"],
        "events": events,
        "layout": {
            "child_depth_observed": child_depth,
            "observed_axis_roles": observed_axes,
            "observed_source_roles": observed_roles,
            "owner_bounded_local_scope": True,
            "sibling_order_is_semantic": False,
            "single_next_page_continuation": (
                region_lines[-1]["page_sequence"] != owner["page_sequence"]
            ),
            "two_group_variant_observed": two_group_variant,
        },
        "negative_family_controls": negative_controls,
        "numeric_token_count": numeric_count,
        "owner": support._line_ref(owner, "FAMILY_OWNER"),
        "page_span": [owner["page_sequence"], region_lines[-1]["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": owner["global_ordinal"],
    }
    if (
        not complete
        and not include_next_page
        and page_index + 1 < len(pages)
        and pages[page_index + 1]["page_sequence"] == owner["page_sequence"] + 1
    ):
        return _region(
            pages,
            page_index,
            owner_index,
            include_next_page=True,
        )
    return result


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
    for page_index, page in enumerate(parsed):
        owners = []
        for index, line in enumerate(page["lines"]):
            text = line["normalized_text"]
            joined = (
                f"{text} {page['lines'][index + 1]['normalized_text']}"
                if index + 1 < len(page["lines"])
                else text
            )
            if _owner(text) or _owner(joined):
                owners.append(index)
        for owner_index in owners:
            candidates.append(_region(parsed, page_index, owner_index))
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
