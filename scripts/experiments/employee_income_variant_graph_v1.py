"""Bank-blind graph for employee-income disclosure variants."""

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

FORMAT_VERSION = "EMPLOYEE_INCOME_VARIANT_GRAPH_DOCUMENT_V1"
FAMILY_ID = "EMPLOYEE_INCOME"
CLAIM_BOUNDARY = (
    "BANK_BLIND_COMPLETE_PDF_FRESH_VIETOCR_EMPLOYEE_INCOME_OWNER_AVERAGE_"
    "EMPLOYEE_COUNT_INCOME_OR_COMPONENTS_AVERAGE_INCOME_PERIOD_UNIT_AND_"
    "OPTIONAL_ROWS_STRUCTURE_ONLY_NO_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "average_salary_or_severance_policy_alone_can_accept": False,
    "bank_filename_note_or_page_used_as_matching_or_routing": False,
    "complete_pdf_region_enumeration_required": True,
    "fresh_vietocr_transformer_text_required": True,
    "mapping_authority": False,
    "minimum_anchor_combination_size": 2,
    "numeric_authority": False,
    "old_ocr_or_native_transcript_used_as_semantic_text": False,
    "optional_salary_bonus_other_and_average_rows_supported": True,
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


class EmployeeIncomeVariantGraphV1Error(ValueError):
    """The complete-PDF input or employee-income graph drifted."""


def _error(message: str) -> EmployeeIncomeVariantGraphV1Error:
    return EmployeeIncomeVariantGraphV1Error(message)


def _support() -> ModuleType:
    name = "interest_income_graph_support_for_employee_income"
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
    return value in {
        "tinh hinh thu nhap cua nhan vien",
        "tinh hinh thu nhap cua can bo nhan vien",
    }


def _role(text: str) -> str | None:
    value = _strip(text)
    if _owner(value):
        return "OWNER"
    if (
        "so luong nhan vien binh quan" in value
        or "tong so nhan vien binh quan" in value
        or "binh quan so can bo nhan vien" in value
    ):
        return "EMPLOYEE_COUNT"
    if "thu nhap binh quan" in value:
        return "AVERAGE_INCOME"
    if "luong binh quan" in value:
        return "AVERAGE_SALARY"
    if value.startswith("tong quy luong") or value == "tien luong":
        return "SALARY_FUND"
    if value.startswith("thuong"):
        return "BONUS"
    if value.startswith("thu nhap khac"):
        return "OTHER_INCOME"
    if value.startswith("tong thu nhap"):
        return "TOTAL_INCOME"
    if value in {"thu nhap cua nhan vien", "thu nhap cua can bo nhan vien"}:
        return "EMPLOYEE_INCOME"
    return None


def _region(lines: Sequence[Mapping[str, Any]], start: int) -> dict[str, Any]:
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
        if role is not None and role != "OWNER":
            roles.append(role)
            events.append(support._line_ref(line, role))
        numeric_count += support._NUMBER.fullmatch(text) is not None
    observed = list(dict.fromkeys(roles))
    income_present = "EMPLOYEE_INCOME" in observed or "TOTAL_INCOME" in observed
    complete = (
        "EMPLOYEE_COUNT" in observed
        and income_present
        and "AVERAGE_INCOME" in observed
        and period_count >= 2
        and unit_count >= 1
        and numeric_count >= 6
    )
    anchors = [
        "OWNER",
        "EMPLOYEE_COUNT",
        "EMPLOYEE_INCOME_OR_TOTAL",
        "AVERAGE_INCOME",
        "PERIOD_AXIS",
        "UNIT_AXIS",
    ]
    return {
        "anchor_roles": anchors,
        "complete": complete,
        "end_global_ordinal": window[-1]["global_ordinal"],
        "events": events,
        "layout": {
            "direct_employee_income_present": "EMPLOYEE_INCOME" in observed,
            "observed_roles": observed,
            "period_axis_line_count": period_count,
            "salary_components_present": any(
                role in observed for role in ("SALARY_FUND", "BONUS", "OTHER_INCOME")
            ),
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
        "direct_income_region_count": sum(
            item["layout"]["direct_employee_income_present"] for item in regions
        ),
        "near_region_count": len(near),
        "page_count_with_complete_region": len(
            {item["owner"]["page_sequence"] for item in regions}
        ),
        "salary_component_region_count": sum(
            item["layout"]["salary_components_present"] for item in regions
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("employee-income graph fields drifted")
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
        raise _error("employee-income graph identity drifted")
    expected_status = (
        "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        if len(value["regions"]) == 1
        else "UNRESOLVED_NO_UNIQUE_REGION"
    )
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
        raise _error("employee-income disposition drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "eivgv1:graph:" + canonical_json_sha256_v1(material):
        raise _error("employee-income graph ID drifted")
    return canonical_clone_v1(value)


def build_employee_income_variant_graph_document_v1(pages: Any) -> dict[str, Any]:
    parsed = _support()._pages(pages)
    lines = [line for page in parsed for line in page["lines"]]
    candidates = [
        _region(lines, index) for index, line in enumerate(lines) if _owner(line["normalized_text"])
    ]
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
        "status": (
            "ACCEPTED_UNIQUE_VARIANT_GRAPH" if len(regions) == 1 else "UNRESOLVED_NO_UNIQUE_REGION"
        ),
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
        {**material, "result_id": "eivgv1:graph:" + canonical_json_sha256_v1(material)}
    )


def validate_employee_income_variant_graph_replay_v1(value: Any, pages: Any) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_employee_income_variant_graph_document_v1(pages)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("employee-income graph does not replay exactly")
    return supplied
