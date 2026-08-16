"""Bank-blind graph for cash-flow detail on acquired or disposed subsidiaries."""

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

FORMAT_VERSION = "SUBSIDIARY_ACQUISITION_DISPOSAL_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "SUBSIDIARY_ACQUISITION_DISPOSAL"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_SUBSIDIARY_ACQUISITION_OR_"
    "DISPOSAL_OWNER_TOTAL_CONSIDERATION_CASH_SETTLEMENT_AND_ACQUIRED_CASH_"
    "PERIOD_UNIT_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_policy_or_cash_flow_caption_alone_can_accept": False,
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "pair_search_exhausted_before_larger_combinations": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
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


class SubsidiaryAcquisitionDisposalVariantGraphV1Error(ValueError):
    """The complete-PDF input or subsidiary transaction graph drifted."""


def _error(message: str) -> SubsidiaryAcquisitionDisposalVariantGraphV1Error:
    return SubsidiaryAcquisitionDisposalVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_subsidiary_transactions"
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


def _transaction_context(text: str) -> bool:
    value = _strip(text)
    direct_role = _role(value)
    if direct_role is not None:
        return direct_role == "OWNER"
    words = set(value.split())
    return (
        "cong ty con" in value and ("mua" in words or "ban" in words or "thanh ly" in value)
    ) or "hop nhat kinh doanh" in value


def _role(text: str) -> str | None:
    value = _strip(text)
    if "tong gia tri" in value and any(word in value for word in ("mua", "thanh ly")):
        return "TOTAL_CONSIDERATION"
    if "thanh toan bang tien" in value and (
        "phan gia tri" in value or "gia tri mua" in value or "gia tri thanh ly" in value
    ):
        return "CASH_SETTLEMENT"
    if "tien va cac khoan tuong duong tien" in value and (
        "thuc co" in value or "co trong cong ty con" in value or "don vi kinh doanh" in value
    ):
        return "CASH_HELD_BY_SUBSIDIARY"
    if "mua moi" in value and "thanh ly" in value and "cong ty con" in value:
        return "OWNER"
    return None


def _candidate(
    pages: Sequence[Mapping[str, Any]], page_index: int, line_index: int
) -> dict[str, Any]:
    support = _support()
    anchor = pages[page_index]["lines"][line_index]
    window_pages = pages[page_index : page_index + 2]
    window = [line for page in window_pages for line in page["lines"]]
    events = [support._line_ref(anchor, "TRANSACTION_CONTEXT")]
    observed: list[str] = []
    period_count = 0
    unit_count = 0
    numeric_count = 0
    for index, line in enumerate(window):
        text = line["normalized_text"]
        axis = support._axis_role(text)
        if axis is not None:
            events.append(support._line_ref(line, axis))
            period_count += axis == "PERIOD_AXIS"
            unit_count += axis == "UNIT_AXIS"
            continue
        role = _role(text)
        if role is None and index + 1 < len(window):
            following = window[index + 1]["normalized_text"]
            if not support._NUMBER.fullmatch(following):
                role = _role(f"{text} {following}")
        if role is not None:
            observed.append(role)
            events.append(support._line_ref(line, role))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    observed_roles = list(dict.fromkeys(observed))
    required = {
        "TOTAL_CONSIDERATION",
        "CASH_SETTLEMENT",
        "CASH_HELD_BY_SUBSIDIARY",
    }
    complete = (
        required <= set(observed_roles)
        and period_count >= 1
        and unit_count >= 1
        and numeric_count >= 3
    )
    anchors = [
        "TRANSACTION_CONTEXT",
        "TOTAL_CONSIDERATION",
        "CASH_SETTLEMENT",
        "CASH_HELD_BY_SUBSIDIARY",
        "PERIOD_AXIS",
        "UNIT_AXIS",
    ]
    return {
        "anchor": support._line_ref(anchor, "TRANSACTION_CONTEXT"),
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": window[-1]["global_ordinal"],
        "events": events,
        "layout": {
            "observed_roles": observed_roles,
            "period_axis_line_count": period_count,
            "unit_axis_line_count": unit_count,
        },
        "numeric_token_count": numeric_count,
        "page_span": [anchor["page_sequence"], window[-1]["page_sequence"]],
        "pair_anchor_combinations": [list(pair) for pair in itertools.combinations(anchors, 2)],
        "start_global_ordinal": anchor["global_ordinal"],
    }


def _metrics(regions: list[dict[str, Any]], near: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "complete_region_count": len(regions),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {page for item in regions for page in item["page_span"]}
        ),
        "transaction_context_count": len(regions) + len(near),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("subsidiary-transaction graph fields drifted")
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
        raise _error("subsidiary-transaction graph identity drifted")
    expected_status = "COMPLETE" if value["regions"] else "NO_COMPLETE_REGION"
    expected_uniqueness = (
        "UNIQUE_FULL_MATCH"
        if len(value["regions"]) == 1
        else "NO_FULL_MATCH"
        if not value["regions"]
        else "MULTIPLE_FULL_MATCHES"
    )
    if value["status"] != expected_status or value["uniqueness"] != {
        "complete_region_count": len(value["regions"]),
        "status": expected_uniqueness,
    }:
        raise _error("subsidiary-transaction disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "sadvv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("subsidiary-transaction graph ID drifted")
    return canonical_clone_v1(value)


def build_subsidiary_acquisition_disposal_variant_graph_document_v1(
    pages: Any,
) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for page_index, page in enumerate(parsed):
        for line_index, line in enumerate(page["lines"]):
            if not _transaction_context(line["normalized_text"]):
                continue
            key = (line["page_sequence"], line["source_line_index"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(_candidate(parsed, page_index, line_index))
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
        "status": "COMPLETE" if regions else "NO_COMPLETE_REGION",
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
    return _validate(
        {**material, "result_id": "sadvv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_subsidiary_acquisition_disposal_variant_graph_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_subsidiary_acquisition_disposal_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("subsidiary-transaction graph does not replay exactly")
    return supplied
